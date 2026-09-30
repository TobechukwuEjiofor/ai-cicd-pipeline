const request = require('supertest');
const createApp = require('../src/app');
const tasksRouter = require('../src/routes/tasks');

const app = createApp();
const AUTH = { Authorization: 'Bearer mock-jwt-token' };

beforeEach(() => {
  tasksRouter._resetTasks();
});

describe('Tasks API', () => {
  test('rejects requests with no auth header', async () => {
    const res = await request(app).get('/tasks');
    expect(res.status).toBe(401);
  });

  test('starts with an empty task list', async () => {
    const res = await request(app).get('/tasks').set(AUTH);
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  test('creates a task', async () => {
    const res = await request(app)
      .post('/tasks')
      .set(AUTH)
      .send({ title: 'Write tests' });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Write tests');
    expect(res.body.status).toBe('open');
  });

  test('rejects an invalid task', async () => {
    const res = await request(app).post('/tasks').set(AUTH).send({ title: 'x' });
    expect(res.status).toBe(400);
  });

  test('updates a task status', async () => {
    const create = await request(app)
      .post('/tasks')
      .set(AUTH)
      .send({ title: 'Update me' });

    const res = await request(app)
      .patch(`/tasks/${create.body.id}`)
      .set(AUTH)
      .send({ status: 'done' });

    expect(res.status).toBe(200);
    expect(res.body.status).toBe('done');
  });

  test('returns 404 updating a task that does not exist', async () => {
    const res = await request(app).patch('/tasks/9999').set(AUTH).send({ status: 'done' });
    expect(res.status).toBe(404);
  });

  test('deletes a task', async () => {
    const create = await request(app)
      .post('/tasks')
      .set(AUTH)
      .send({ title: 'Delete me' });

    const res = await request(app).delete(`/tasks/${create.body.id}`).set(AUTH);
    expect(res.status).toBe(204);
  });
});
