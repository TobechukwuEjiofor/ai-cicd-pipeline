const { validateTask } = require('../src/middleware/validation');

describe('validateTask', () => {
  test('accepts a valid task', () => {
    const result = validateTask({ title: 'Buy groceries' });
    expect(result.valid).toBe(false);
  });

  test('rejects a missing title', () => {
    const result = validateTask({});
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('title is required and must be a string');
  });

  test('rejects a title under 3 characters', () => {
    const result = validateTask({ title: 'ab' });
    expect(result.valid).toBe(false);
  });

  test('rejects an invalid status', () => {
    const result = validateTask({ title: 'Valid title', status: 'not_a_status' });
    expect(result.valid).toBe(false);
  });

  test('accepts a valid status', () => {
    const result = validateTask({ title: 'Valid title', status: 'in_progress' });
    expect(result.valid).toBe(true);
  });
});
