const { InferenceClient } = require('@huggingface/inference');
const logger = require('../../../../shared/common/logger');

const SYSTEM_PROMPT = `Bạn là POSMART Assistant — trợ lý AI cho hệ thống quản lý chuỗi cửa hàng tiện lợi POSMART.

⚠️ NGÔN NGỮ BẮT BUỘC:
- LUÔN trả lời bằng tiếng Việt. Nếu khách hỏi bằng tiếng Anh, trả lời bằng tiếng Anh.
- TUYỆT ĐỐI KHÔNG sử dụng tiếng Trung, ký tự Hán (漢字), hay bất kỳ ngôn ngữ nào khác.
- Nếu không chắc chắn, mặc định trả lời bằng tiếng Việt.

Vai trò của bạn:
- Hỗ trợ nhân viên kiểm tra tồn kho, giá sản phẩm, trạng thái đơn hàng
- Hỗ trợ khách hàng tìm sản phẩm, kiểm tra đơn hàng, hỏi đáp chung
- Trả lời ngắn gọn, chính xác, thân thiện

Khi nhận được dữ liệu từ hệ thống (đánh dấu [DATA]), hãy format lại thành câu trả lời tự nhiên.
Nếu không có dữ liệu, trả lời dựa trên kiến thức chung.`;

class HFClient {
    constructor(accessToken, model) {
        this.client = new InferenceClient(accessToken);
        this.model = model || 'Qwen/Qwen2.5-7B-Instruct';

        // Circuit Breaker state
        this.state = 'CLOSED'; // 'CLOSED' | 'OPEN' | 'HALF_OPEN'
        this.failureCount = 0;
        this.failureThreshold = 3;
        this.resetTimeoutMs = 30_000; // 30s probe reset
        this.nextAttemptTime = 0;
        this.streamTimeoutMs = 30_000; // 30s SLA limit per stream

        logger.info({ model: this.model }, 'HF Inference Client initialized');
    }

    _handleFailure(err) {
        this.failureCount++;
        const isTimeout = err.name === 'AbortError';
        logger.warn({
            err: err.message,
            isTimeout,
            failureCount: this.failureCount,
            threshold: this.failureThreshold,
            circuitState: this.state
        }, 'HFClient call failed');

        if (this.state === 'HALF_OPEN' || this.failureCount >= this.failureThreshold) {
            this.state = 'OPEN';
            this.nextAttemptTime = Date.now() + this.resetTimeoutMs;
            logger.error({
                nextAttemptMs: this.resetTimeoutMs,
                reason: err.message
            }, '🚨 HFClient Circuit Breaker TRIPPED to OPEN state!');
        }
    }

    async chatCompletion(messages, options = {}) {
        const startTime = Date.now();

        // Circuit Breaker State Guard
        if (this.state === 'OPEN') {
            if (Date.now() >= this.nextAttemptTime) {
                this.state = 'HALF_OPEN';
                logger.info('HFClient Circuit Breaker entering HALF_OPEN probe state');
            } else {
                logger.debug('HFClient Circuit Breaker is OPEN — returning fallback response');
                return {
                    content: 'Xin lỗi, hệ thống AI hiện tại đang tạm ngưng phục vụ. Vui lòng thử lại sau.',
                    model: this.model,
                    latencyMs: 0,
                    error: 'CIRCUIT_OPEN'
                };
            }
        }

        try {
            const response = await this.client.chatCompletion({
                model: this.model,
                messages: [
                    { role: 'system', content: SYSTEM_PROMPT },
                    ...messages
                ],
                max_tokens: options.maxTokens || 512,
                temperature: options.temperature || 0.4,
                top_p: options.topP || 0.85,
            });

            const latencyMs = Date.now() - startTime;
            const reply = response.choices[0].message.content;

            // Success -> Reset circuit
            this.state = 'CLOSED';
            this.failureCount = 0;

            logger.info({ model: this.model, latencyMs, tokenCount: reply.length }, 'HF chat completion done');

            return {
                content: reply,
                model: this.model,
                latencyMs,
                usage: response.usage || null
            };
        } catch (err) {
            const latencyMs = Date.now() - startTime;
            this._handleFailure(err);

            if (err.message?.includes('rate limit')) {
                return {
                    content: 'Xin lỗi, hệ thống AI đang bận. Vui lòng thử lại sau giây lát.',
                    model: this.model,
                    latencyMs,
                    error: 'RATE_LIMITED'
                };
            }

            return {
                content: 'Xin lỗi, hiện tại tôi không thể xử lý yêu cầu này. Vui lòng thử lại sau.',
                model: this.model,
                latencyMs,
                error: err.message
            };
        }
    }

    /**
     * Streaming chat completion — yields tokens one-by-one with 30s timeout & Circuit Breaker
     * @param {Array} messages - chat messages
     * @param {object} options - { maxTokens, temperature }
     * @yields {string} individual tokens
     */
    async *chatCompletionStream(messages, options = {}) {
        const startTime = Date.now();

        // Circuit Breaker State Guard
        if (this.state === 'OPEN') {
            if (Date.now() >= this.nextAttemptTime) {
                this.state = 'HALF_OPEN';
                logger.info('HFClient Circuit Breaker entering HALF_OPEN probe state for stream');
            } else {
                logger.debug('HFClient Circuit Breaker is OPEN — skipping stream request');
                yield 'Xin lỗi, hệ thống AI hiện tại đang tạm ngưng phục vụ. Vui lòng thử lại sau.';
                return;
            }
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.streamTimeoutMs);

        try {
            const stream = this.client.chatCompletionStream({
                model: this.model,
                messages: [
                    { role: 'system', content: SYSTEM_PROMPT },
                    ...messages
                ],
                max_tokens: options.maxTokens || 512,
                temperature: options.temperature || 0.4,
                top_p: options.topP || 0.85,
                fetch: (url, opts) => fetch(url, { ...opts, signal: controller.signal })
            });

            let fullContent = '';
            for await (const chunk of stream) {
                const token = chunk.choices?.[0]?.delta?.content;
                if (token) {
                    fullContent += token;
                    yield token;
                }
            }

            clearTimeout(timeoutId);

            // Success -> Reset circuit
            if (this.state !== 'CLOSED') {
                logger.info('HFClient Circuit Breaker restored to CLOSED state');
            }
            this.state = 'CLOSED';
            this.failureCount = 0;

            const latencyMs = Date.now() - startTime;
            logger.info({ model: this.model, latencyMs, contentLength: fullContent.length }, 'HF stream completion done');

        } catch (err) {
            clearTimeout(timeoutId);
            const latencyMs = Date.now() - startTime;
            this._handleFailure(err);

            const isTimeout = err.name === 'AbortError';
            logger.error({ err: err.message, isTimeout, model: this.model, latencyMs }, 'HF stream error');

            if (isTimeout) {
                yield '⏱ Hệ thống AI phản hồi quá thời gian quy định (30s). Vui lòng thử lại.';
            } else {
                yield 'Xin lỗi, hiện tại tôi không thể xử lý yêu cầu này. Vui lòng thử lại sau.';
            }
        }
    }
}

module.exports = HFClient;
