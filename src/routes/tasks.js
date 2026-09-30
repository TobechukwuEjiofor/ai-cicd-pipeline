const express = require('express');
const router = express.Router();
const { requireAuth } = require('../middleware/auth');
const { validateTask } = require('../middleware/validation');

let tasks = [];
let nextId = 1;

router.use(requireAuth);

router.get('/', (req, res) => {
  res.json(tasks);
});

router.post('/', (req, res) => {
  const { valid, errors } = validateTask(req.body);
  if (!valid) return res.status(400).json({ errors });

  const task = {
    id: nextId++,
    title: req.body.title,
    description: req.body.description || '',
    status: 'open',
  };
  tasks.push(task);
  res.status(201).json(task);
});

router.patch('/:id', (req, res) => {
  const task = tasks.find((t) => t.id === Number(req.params.id));
  if (!task) return res.status(404).json({ error: 'Task not found' });

  const { status } = req.body;
  if (!status || !['open', 'in_progress', 'done'].includes(status)) {
    return res.status(400).json({ error: 'Invalid status' });
  }
  task.status = status;
  res.json(task);
});

router.delete('/:id', (req, res) => {
  const index = tasks.findIndex((t) => t.id === Number(req.params.id));
  if (index === -1) return res.status(404).json({ error: 'Task not found' });
  tasks.splice(index, 1);
  res.status(204).send();
});

// Lets tests reset the in-memory list between test cases
router._resetTasks = () => {
  tasks = [];
  nextId = 1;
};

module.exports = router;
