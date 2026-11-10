export class EmailParser {
  // Parses host instruction email: "Infosys | 2026-11-10 | 14:30 | Virtual"
  static parseHostCommand(subject) {
    const parts = subject.split('|').map(p => p.trim());
    if (parts.length < 4) return null;
    return {
      company: parts[0],
      date: parts[1],
      time: parts[2],
      type: parts[3]
    };
  }

  // Parses tracking addresses from incoming email headers (e.g. event-12345@domain.com)
  static extractTrackingHash(toEmailHeader) {
    const match = toEmailHeader.match(/event-([^@]+)@/);
    if (!match) return null;
    
    // Decodes Base64 safe strings containing event details
    try {
      const decoded = Buffer.from(match[1], 'hex').toString('utf8');
      return JSON.parse(decoded); // Returns {company, date, time, type}
    } catch {
      return null;
    }
  }
}
