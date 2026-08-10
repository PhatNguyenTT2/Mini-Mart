jest.mock('../../../../shared/common/logger', () => ({
  debug: jest.fn(),
  info: jest.fn(),
  warn: jest.fn(),
  error: jest.fn()
}));

const AIClient = require('../../src/services/ai.client');

const response = (rankings, overrides = {}) => ({
  ok: true,
  status: 200,
  statusText: 'OK',
  json: async () => ({ rankings, inference_ms: 0.2, ...overrides })
});

describe('AIClient production contract', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    jest.useRealTimers();
  });

  it('propagates store and preserves nullable user, persona and context', async () => {
    global.fetch.mockResolvedValue(response([
      { product_id: 11, rank: 1, ai_score: 2.5 },
      { product_id: 12, rank: 2, ai_score: 1.5 }
    ]));
    const client = new AIClient('http://ai:8000');

    await client.scoreProducts({
      storeId: 7,
      userId: null,
      personaCluster: null,
      candidateProductIds: [11, 12],
      contextProductId: null
    });

    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body).toEqual({
      store_id: 7,
      user_id: null,
      persona_cluster: null,
      candidate_product_ids: [11, 12],
      context_product_id: null
    });
  });

  it.each([
    [[{ product_id: 11, rank: 1, ai_score: Number.NaN }]],
    [[{ product_id: 11, rank: 1, ai_score: 1 }, { product_id: 11, rank: 2, ai_score: 0 }]],
    [[{ product_id: 11, rank: 1, ai_score: 1 }]]
  ])('falls back when rankings are malformed or incomplete', async rankings => {
    global.fetch.mockResolvedValue(response(rankings));
    const client = new AIClient('http://ai:8000', { failureThreshold: 1 });
    const candidates = rankings.length === 1 && Number.isFinite(rankings[0].ai_score)
      ? [11, 12]
      : [11];

    await expect(client.scoreProducts({
      storeId: 1,
      userId: 2,
      personaCluster: 3,
      candidateProductIds: candidates,
      contextProductId: 11
    })).resolves.toBeNull();
    expect(client.getState().state).toBe('OPEN');
  });

  it('opens on timeout, probes HALF_OPEN, then recovers CLOSED', async () => {
    let now = 1_000;
    jest.spyOn(Date, 'now').mockImplementation(() => now);
    global.fetch.mockRejectedValueOnce(Object.assign(new Error('timeout'), { name: 'AbortError' }));
    const client = new AIClient('http://ai:8000', {
      failureThreshold: 1,
      resetTimeoutMs: 50
    });
    const request = {
      storeId: 1,
      userId: 2,
      personaCluster: 3,
      candidateProductIds: [11],
      contextProductId: null
    };

    await expect(client.scoreProducts(request)).resolves.toBeNull();
    expect(client.getState().state).toBe('OPEN');
    expect(global.fetch).toHaveBeenCalledTimes(1);
    await expect(client.scoreProducts(request)).resolves.toBeNull();
    expect(global.fetch).toHaveBeenCalledTimes(1);

    now += 51;
    global.fetch.mockResolvedValueOnce(response([{ product_id: 11, rank: 1, ai_score: 1 }]));
    await expect(client.scoreProducts(request)).resolves.toHaveLength(1);
    expect(client.getState().state).toBe('CLOSED');
    Date.now.mockRestore();
  });
});
