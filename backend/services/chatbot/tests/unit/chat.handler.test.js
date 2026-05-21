const jwt = require('jsonwebtoken');

// Mock logger
jest.mock('../../../../shared/common/logger', () => ({
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn()
}));

const initChatSocket = require('../../src/ws/chat.handler');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

describe('WebSocket Chat Handler', () => {
    let mockIo;
    let mockSocket;
    let mockChatService;
    let connectionHandler;

    beforeEach(() => {
        mockChatService = {
            startSession: jest.fn().mockResolvedValue({ id: 1, user_id: 10, is_active: true }),
            sendMessageStream: jest.fn().mockImplementation(async function* (sessionId, message) {
                yield { type: 'chunk', text: 'Hello' };
                yield {
                    type: 'complete',
                    intent: 'FREE_CHAT',
                    fullText: 'Hello there!',
                    metadata: { model: 'test', latencyMs: 100 },
                    products: null,
                    suggestedPrompts: null
                };
            }),
            endSession: jest.fn().mockResolvedValue({ id: 1, is_active: false }),
            getSession: jest.fn().mockResolvedValue({ id: 1, is_active: true }),
            getSessionMessages: jest.fn().mockResolvedValue([
                { id: 1, role: 'user', content: 'Hi' },
                { id: 2, role: 'assistant', content: 'Hello!' }
            ])
        };

        // Build mock socket
        mockSocket = {
            id: 'socket-123',
            user: { id: 10, role: 'Employee', storeId: 1 },
            handshake: { auth: { token: jwt.sign({ id: 10, role: 'Employee', storeId: 1 }, JWT_SECRET) } },
            join: jest.fn(),
            leave: jest.fn(),
            emit: jest.fn(),
            to: jest.fn().mockReturnThis(),
            on: jest.fn()
        };

        // Capture event handlers registered by on()
        const eventHandlers = {};
        mockSocket.on.mockImplementation((event, handler) => {
            eventHandlers[event] = handler;
        });

        // Build mock io
        const authMiddlewares = [];
        mockIo = {
            use: jest.fn((fn) => authMiddlewares.push(fn)),
            on: jest.fn((event, handler) => {
                if (event === 'connection') connectionHandler = handler;
            })
        };

        initChatSocket(mockIo, mockChatService);

        // Trigger connection
        connectionHandler(mockSocket);

        // Expose event handlers for testing
        mockSocket._handlers = eventHandlers;
    });

    describe('Auth Middleware', () => {
        it('should register auth middleware', () => {
            expect(mockIo.use).toHaveBeenCalled();
        });

        it('should reject connection without token', () => {
            const authMiddleware = mockIo.use.mock.calls[0][0];
            const noAuthSocket = { handshake: { auth: {}, headers: {} } };
            const next = jest.fn();

            authMiddleware(noAuthSocket, next);

            expect(next).toHaveBeenCalledWith(expect.any(Error));
            expect(next.mock.calls[0][0].message).toContain('UNAUTHORIZED');
        });

        it('should accept valid token', () => {
            const authMiddleware = mockIo.use.mock.calls[0][0];
            const validToken = jwt.sign({ id: 1, role: 'Employee' }, JWT_SECRET);
            const authSocket = { handshake: { auth: { token: validToken }, headers: {} } };
            const next = jest.fn();

            authMiddleware(authSocket, next);

            expect(next).toHaveBeenCalledWith();
            expect(authSocket.user).toBeDefined();
            expect(authSocket.user.id).toBe(1);
        });
    });

    describe('chat:join_session', () => {
        it('should create session and join room', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:join_session']({}, callback);

            expect(mockChatService.startSession).toHaveBeenCalledWith(10, 'employee', 1);
            expect(mockSocket.join).toHaveBeenCalledWith('session:1');
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
            expect(mockSocket.emit).toHaveBeenCalledWith('chat:session_ready', expect.any(Object));
        });
    });

    describe('chat:send_message', () => {
        it('should process message and emit response', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:send_message'](
                { session_id: 1, message: 'Hello!' },
                callback
            );

            expect(mockChatService.sendMessageStream).toHaveBeenCalledWith(1, 'Hello!');
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                success: true,
                data: expect.objectContaining({ intent: 'FREE_CHAT', fullText: 'Hello there!' })
            }));
            expect(mockSocket.emit).toHaveBeenCalledWith('chat:stream_complete', expect.any(Object));
        });

        it('should emit typing indicator before processing', async () => {
            await mockSocket._handlers['chat:send_message'](
                { session_id: 1, message: 'Hello!' },
                jest.fn()
            );

            expect(mockSocket.emit).toHaveBeenCalledWith('chat:typing', { session_id: 1, is_typing: true });
        });

        it('should handle error for missing data', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:send_message']({}, callback);

            expect(callback).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
        });
    });

    describe('chat:confirm_action', () => {
        it('should handle confirm: true by sending "Đồng ý"', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:confirm_action'](
                { session_id: 1, confirm: true },
                callback
            );

            expect(mockChatService.sendMessageStream).toHaveBeenCalledWith(1, 'Đồng ý');
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                success: true,
                data: expect.objectContaining({ intent: 'FREE_CHAT', fullText: 'Hello there!' })
            }));
            expect(mockSocket.emit).toHaveBeenCalledWith('chat:stream_complete', expect.any(Object));
        });

        it('should handle confirm: false by sending "Không"', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:confirm_action'](
                { session_id: 1, confirm: false },
                callback
            );

            expect(mockChatService.sendMessageStream).toHaveBeenCalledWith(1, 'Không');
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
        });

        it('should emit typing indicator before processing confirmation', async () => {
            await mockSocket._handlers['chat:confirm_action'](
                { session_id: 1, confirm: true },
                jest.fn()
            );

            expect(mockSocket.emit).toHaveBeenCalledWith('chat:typing', { session_id: 1, is_typing: true });
        });

        it('should handle error for missing session_id or confirm', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:confirm_action']({ session_id: 1 }, callback);

            expect(callback).toHaveBeenCalledWith(expect.objectContaining({ success: false }));
        });
    });

    describe('chat:end_session', () => {
        it('should end session and leave room', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:end_session']({ session_id: 1 }, callback);

            expect(mockChatService.endSession).toHaveBeenCalledWith(1);
            expect(mockSocket.leave).toHaveBeenCalledWith('session:1');
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({ success: true }));
        });
    });

    describe('chat:get_history', () => {
        it('should return session with messages', async () => {
            const callback = jest.fn();
            await mockSocket._handlers['chat:get_history']({ session_id: 1 }, callback);

            expect(mockChatService.getSession).toHaveBeenCalledWith(1);
            expect(mockChatService.getSessionMessages).toHaveBeenCalledWith(1);
            expect(callback).toHaveBeenCalledWith(expect.objectContaining({
                success: true,
                data: expect.objectContaining({ messages: expect.any(Array) })
            }));
        });
    });

    describe('disconnect', () => {
        it('should register disconnect handler', () => {
            expect(mockSocket._handlers['disconnect']).toBeDefined();
        });
    });
});
