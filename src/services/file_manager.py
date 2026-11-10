import fs from 'fs';
import path from 'path';
import { STORAGE_ROOT } from '../../config/database.js';
import { parse } from 'csv-parse/sync';
import { stringify } from 'csv-stringify/sync';

export class FileManager {
  static getFilePath(company, date, time, type) {
    // Sanitise values to create valid directory names
    const safeCompany = company.replace(/[^a-aZ-Z0-9]/g, '_');
    const safeDate = date.replace(/[^a-aZ-Z0-9]/g, '-');
    const safeTime = time.replace(/[^a-aZ-Z0-9]/g, '-');
    const safeType = type.toLowerCase().trim();

    const dirPath = path.join(STORAGE_ROOT, safeCompany, safeDate);
    const fileName = `${safeTime}_${safeType}_guests.csv`;
    
    return { dirPath, fullPath: path.join(dirPath, fileName) };
  }

  static createEventFile(company, date, time, type) {
    const { dirPath, fullPath } = this.getFilePath(company, date, time, type);

    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }

    if (!fs.existsSync(fullPath)) {
      const headers = [['Email', 'RSVP_Status', 'Last_Updated']];
      const csvContent = stringify(headers);
      fs.writeFileSync(fullPath, csvContent, 'utf8');
      console.log(`[File Manager] Created new event file: ${fullPath}`);
    }
    return fullPath;
  }

  static updateParticipantStatus(fullPath, participantEmail, status) {
    if (!fs.existsSync(fullPath)) return false;

    const fileContent = fs.readFileSync(fullPath, 'utf8');
    let records = parse(fileContent, { columns: true, skip_empty_lines: true });
    
    let found = false;
    records = records.map(row => {
      if (row.Email.toLowerCase() === participantEmail.toLowerCase()) {
        found = true;
        return { Email: row.Email, RSVP_Status: status, Last_Updated: new Date().toISOString() };
      }
      return row;
    });

    if (!found) {
      records.push({ Email: participantEmail, RSVP_Status: status, Last_Updated: new Date().toISOString() });
    }

    const updatedCsv = stringify(records, { header: true });
    fs.writeFileSync(fullPath, updatedCsv, 'utf8');
    return true;
  }
}
