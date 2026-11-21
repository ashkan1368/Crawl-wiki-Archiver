import express from 'express';
import { execFile } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';
import { createServer as createViteServer } from 'vite';

const execFileAsync = promisify(execFile);

async function runPythonAction(action: string, payload: Record<string, unknown> = {}) {
  const { stdout } = await execFileAsync(
    'python3',
    ['-m', 'wikiran_archive.main', '--api', action, '--payload', JSON.stringify(payload)],
    {
      cwd: process.cwd(),
      maxBuffer: 10 * 1024 * 1024,
    }
  );
  return JSON.parse(stdout);
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '2mb' }));

  app.get('/api/overview', async (_req, res) => {
    try {
      const data = await runPythonAction('overview');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/search', async (req, res) => {
    try {
      const data = await runPythonAction('search', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/settings', async (req, res) => {
    try {
      const data = await runPythonAction('set_settings', { settings: req.body || {} });
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/schedule', async (req, res) => {
    try {
      const data = await runPythonAction('schedule_update', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/schedule/run-now', async (_req, res) => {
    try {
      const data = await runPythonAction('schedule_run_now', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/update-archive', async (req, res) => {
    try {
      const data = await runPythonAction('update_archive', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/crawl-status', async (_req, res) => {
    try {
      const data = await runPythonAction('crawl_status', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/stop-crawl', async (_req, res) => {
    try {
      const data = await runPythonAction('stop_crawl', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/ofac/status', async (_req, res) => {
    try {
      const data = await runPythonAction('ofac_status', {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/ofac/sync', async (req, res) => {
    try {
      const data = await runPythonAction('ofac_sync', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/resume-job', async (req, res) => {
    try {
      const data = await runPythonAction('resume_job', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/reconnaissance', async (_req, res) => {
    try {
      const data = await runPythonAction('reconnaissance');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/export/:format', async (req, res) => {
    try {
      const fmt = (req.params.format || 'xlsx').toLowerCase();
      const rawEntities = typeof req.query.entities === 'string' ? req.query.entities : '';
      const entities = rawEntities
        ? rawEntities
            .split(',')
            .map((e) => e.trim().toLowerCase())
            .filter(Boolean)
        : undefined;
      const date_from =
        typeof req.query.date_from === 'string' && req.query.date_from.trim()
          ? req.query.date_from.trim()
          : undefined;
      const date_to =
        typeof req.query.date_to === 'string' && req.query.date_to.trim()
          ? req.query.date_to.trim()
          : undefined;
      const data = await runPythonAction('export', { format: fmt, entities, date_from, date_to });
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Export file could not be generated.' });
        return;
      }
      res.download(data.path, data.filename);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/csv/import', async (req, res) => {
    try {
      const data = await runPythonAction('csv_import', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/csv/view', async (req, res) => {
    try {
      const data = await runPythonAction('csv_view', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/csv/download/:datasetId', async (req, res) => {
    try {
      const datasetId = Number(req.params.datasetId);
      const data = await runPythonAction('csv_view', { dataset_id: datasetId });
      const xlsxPath = data?.active_csv?.dataset?.xlsx_export_path;
      if (!xlsxPath || !fs.existsSync(xlsxPath)) {
        res.status(404).json({ ok: false, error: 'Converted Excel file not found.' });
        return;
      }
      res.download(xlsxPath, path.basename(xlsxPath));
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-package', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_package');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({ ok: false, error: 'Windows 11 package could not be generated.' });
        return;
      }
      res.download(data.path, data.filename || 'WikIran_Archive_Windows11_Clerk_Edition.zip');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-installer-exe', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_installer_exe');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows installer .exe could not be generated.',
        });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Setup.exe');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-shortcut', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_installer_exe');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows installer .exe could not be generated.',
        });
        return;
      }
      res.download(data.path, data.filename || 'WikIranArchive_Setup.exe');
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/download/windows-app-html', async (_req, res) => {
    try {
      const data = await runPythonAction('windows_app_html');
      if (!data.ok || !data.path || !fs.existsSync(data.path)) {
        res.status(500).json({
          ok: false,
          error: 'Windows 11 ready app could not be generated.',
        });
        return;
      }
      res.download(
        data.path,
        data.filename || 'WikIran_Archive_Windows11_Ready_App.html'
      );
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/create', async (_req, res) => {
    try {
      const data = await runPythonAction('backup_create');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/backup/restore', async (req, res) => {
    try {
      const data = await runPythonAction('backup_restore', req.body || {});
      res.json(data);
    } catch (err) {
      res.status(400).json({ ok: false, error: String(err) });
    }
  });

  app.post('/api/integrity-check', async (_req, res) => {
    try {
      const data = await runPythonAction('integrity_check');
      res.json(data);
    } catch (err) {
      res.status(500).json({ ok: false, error: String(err) });
    }
  });

  app.get('/api/tests', async (_req, res) => {
    try {
      const { stdout, stderr } = await execFileAsync(
        'python3',
        ['-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        { cwd: process.cwd() }
      );
      res.json({ ok: true, output: `${stdout}\n${stderr}`.trim() });
    } catch (err: unknown) {
      const e = err as { stdout?: string; stderr?: string; message?: string };
      res.json({
        ok: false,
        output: `${e.stdout || ''}\n${e.stderr || e.message || ''}`.trim(),
      });
    }
  });

  const DOC_FILES: Record<string, string> = {
    reconnaissance: 'RECONNAISSANCE_REPORT.md',
    architecture: 'ARCHITECTURE.md',
    schema: 'DATABASE_SCHEMA.md',
    manual_fa: 'OPERATOR_MANUAL_FA.md',
    manual_en: 'OPERATOR_MANUAL_EN.md',
    status: 'PROJECT_STATUS.md',
    pyside_ui: 'wikiran_archive/ui/main_window.py',
    migrations_py: 'wikiran_archive/database/migrations.py',
    recon_py: 'wikiran_archive/collector/reconnaissance.py',
  };

  app.get('/api/docs/:key', (req, res) => {
    const relPath = DOC_FILES[req.params.key];
    if (!relPath) {
      res.status(404).json({ ok: false, error: 'Document not found' });
      return;
    }
    const fullPath = path.resolve(process.cwd(), relPath);
    if (!fs.existsSync(fullPath)) {
      res.status(404).json({ ok: false, error: 'File missing on disk' });
      return;
    }
    res.json({
      ok: true,
      filename: relPath,
      content: fs.readFileSync(fullPath, 'utf-8'),
    });
  });

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`WikIran Archive Desktop Bridge running on http://localhost:${PORT}`);
  });
}

startServer();
