import 'dotenv/config';
import express from 'express';
import { initDatabase } from '../config/database.js';
import inboundRouter from './webhooks/inbound_receiver.js';

const app = express();
const PORT = process.env.PORT || 3000;

// Enable raw body and json parsing middleware frameworks
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Local CSV Directories system paths
initDatabase();

// Connect Routing Endpoints
app.use('/api/v1', inboundRouter);

app.listen(PORT, () => {
  console.log(`===============================================`);
  console.log(` Luma-Email Engine Running on Port: ${PORT}   `);
  console.log(`===============================================`);
});
