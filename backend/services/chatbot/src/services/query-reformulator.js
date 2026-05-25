/**
 * QueryReformulator — Rewrite ambiguous follow-up questions
 * 
 * Two reformulation strategies:
 * 1. PRONOUNS ("nó", "cái đó") → LLM-based rewriting with chat history
 * 2. CONTINUATION ("gợi ý thêm", "có gì khác") → Deterministic: reuse last substantive query
 *    (No LLM call — 100% reliable for demo stability)
 */
const logger = require('../../../../shared/common/logger');

const VIETNAMESE_PRONOUNS = [
    'nó', 'cái đó', 'cái này', 'cái kia', 'loại này', 'loại đó',
    'món đó', 'món này', 'thế', 'vậy', 'sản phẩm đó', 'hàng đó'
];

// Continuation patterns: user wants "more of the same" without specifying what
const CONTINUATION_PATTERNS = [
    'gợi ý thêm', 'thêm đi', 'có gì khác', 'cho xem thêm', 'cho xem tiếp',
    'còn gì', 'còn loại nào', 'khác không', 'nữa không', 'nữa đi',
    'gợi ý khác', 'xem thêm', 'tìm thêm', 'recommend thêm', 'suggest thêm'
];

class QueryReformulator {
    constructor(hfClient) {
        this.hfClient = hfClient;
    }

    /**
     * Reformulate a user message if it contains ambiguous pronouns or continuation patterns
     * @param {string} userMessage - current user message
     * @param {object[]} chatHistory - recent messages [{role, content}]
     * @returns {string} standalone query (original or rewritten)
     */
    async reformulate(userMessage, chatHistory) {
        if (!this._needsReformulation(userMessage)) return userMessage;
        if (!chatHistory?.length) return userMessage;

        // Strategy 1: CONTINUATION patterns — deterministic, no LLM
        // Reuse the last substantive user query (skip other continuations)
        if (this._isContinuation(userMessage)) {
            const lastTopic = this._extractLastTopic(chatHistory);
            if (lastTopic) {
                logger.info({ original: userMessage, reformulated: lastTopic, strategy: 'continuation' }, 'Query reformulated');
                return lastTopic;
            }
            // No topic found in history — fall through to LLM
        }

        // Strategy 2: PRONOUN patterns — LLM-based rewriting
        try {
            const startTime = Date.now();

            // Build minimal history for context (last 4 messages)
            const recentHistory = chatHistory.slice(-4);
            const historyText = recentHistory
                .map(m => `${m.role === 'user' ? 'Khách' : 'Bot'}: ${m.content}`)
                .join('\n');

            const prompt = `Dựa trên lịch sử hội thoại, viết lại câu hỏi sau thành câu hoàn chỉnh, độc lập, không cần ngữ cảnh.

Lịch sử:
${historyText}

Câu hỏi hiện tại: "${userMessage}"

Viết lại ngắn gọn (chỉ trả về câu viết lại, không giải thích):`;

            const result = await this.hfClient.chatCompletion(
                [{ role: 'user', content: prompt }],
                { maxTokens: 100, temperature: 0.3 }
            );

            const reformulated = result.content?.trim();
            const latencyMs = Date.now() - startTime;

            if (reformulated && reformulated.length > 3 && reformulated.length < 200) {
                logger.info({ original: userMessage, reformulated, latencyMs, strategy: 'llm' }, 'Query reformulated');
                return reformulated;
            }

            return userMessage;
        } catch (err) {
            logger.warn({ err, message: userMessage }, 'Query reformulation failed — using original');
            return userMessage;
        }
    }

    /**
     * Extract the last substantive user query from chat history
     * Skips continuation/filler messages to find the real topic
     * @returns {string|null}
     */
    _extractLastTopic(chatHistory) {
        const userMessages = chatHistory
            .filter(m => m.role === 'user')
            .map(m => m.content)
            .reverse(); // newest first

        for (const msg of userMessages) {
            const lower = msg.toLowerCase();
            // Skip if this message is itself a continuation or very short filler
            const isCont = CONTINUATION_PATTERNS.some(p => lower.includes(p));
            const isFiller = lower.length < 5 || ['ok', 'vâng', 'đồng ý', 'không', 'có'].includes(lower.trim());
            if (!isCont && !isFiller) {
                return msg;
            }
        }
        return null;
    }

    /**
     * Check if message is a continuation pattern
     */
    _isContinuation(msg) {
        const lower = msg.toLowerCase();
        return CONTINUATION_PATTERNS.some(p => lower.includes(p));
    }

    /**
     * Check if message contains ambiguous pronouns or continuation patterns
     */
    _needsReformulation(msg) {
        const lower = msg.toLowerCase();
        const hasPronoun = VIETNAMESE_PRONOUNS.some(p => lower.includes(p));
        return hasPronoun || this._isContinuation(msg);
    }
}

module.exports = QueryReformulator;
