function requireAuth(req, res, next) {
  const header = req.headers.authorization;
  if (!header || header !== 'Bearer mock-jwt-token') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

module.exports = { requireAuth };
