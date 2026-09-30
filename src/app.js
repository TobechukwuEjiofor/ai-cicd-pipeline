// Express app factory
// Express app factory
const express = require('express');
const authRoutes = require('./routes/auth');
const tasksRoutes = require('./routes/tasks');

function createApp() {
  const app = express();
  app.use(express.json());
  app.use('/auth', authRoutes);
  app.use('/tasks', tasksRoutes);
  app.get('/health', (req, res) => res.json({ status: 'ok' }));
  return app;
}

module.exports = createApp;
