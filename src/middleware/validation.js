function validateTask(body) {
  const errors = [];

  if (!body.title || typeof body.title !== 'string') {
    errors.push('title is required and must be a string');
  } else if (body.title.trim().length < 3) {
    errors.push('title must be at least 3 characters');
  }

  if (body.status && !['open', 'in_progress', 'done'].includes(body.status)) {
    errors.push('status must be one of open, in_progress, done');
  }

  return { valid: errors.length === 0, errors };
}

module.exports = { validateTask };
