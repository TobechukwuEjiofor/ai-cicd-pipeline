const request = require('supertest');
const createApp = require('../src/app');

const app = createApp();

describe('POST /auth/login', () => {
  test('returns a token for valid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({ username: 'admin', password: 'password123' });
    expect(res.status).toBe(200);
    expect(res.body.token).toBe('mock-jwt-token');
  });

  test('rejects invalid credentials', async () => {
    const res = await request(app)
      .post('/auth/login')
      .send({ username: 'admin', password: 'wrongpassword' });
    expect(res.status).toBe(401);
  });
});
