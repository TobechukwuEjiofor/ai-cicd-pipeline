const createApp = require('./app');

const app = createApp();
const PORT = process.env.PORT || 4000;

app.listen(PORT, () => console.log(`Task manager API running on port ${PORT}`));
