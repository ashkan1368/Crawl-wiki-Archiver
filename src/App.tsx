import React, { useEffect, useState, useCallback } from 'react';
import {
  Search,
  BookOpen,
  FolderKanban,
  Building2,
  Tags,
  FileSpreadsheet,
  History,
  Settings,
  HelpCircle,
  LayoutDashboard,
  RefreshCw,
  HardDriveDownload,
  ShieldCheck,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Play,
  FileCode2,
  Globe,
  Clock,
  Table,
  Upload,
  Menu,
  X,
  Eye,
  Unlock,
  Lock,
  Layers,
  Wifi,
  WifiOff,
  Square,
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Language, NavSection, UI_LABELS } from './i18n';

interface Article {
  id: number;
  original_pub_id: string;
  title: string;
  subtitle: string;
  author: string;
  publication_date: string;
  summary: string;
  editorial_content: string;
  categories_en: string;
  categories_fa: string;
  organizations_list: string;
  tags_list: string;
  source_url: string;
  retrieved_at: string;
  last_verified_at: string;
  extraction_status: string;
  content_hash: string;
  record_version: number;
}

interface Publication {
  id: number;
  original_pub_id: string;
  title: string;
  native_title: string;
  publication_date: string;
  description: string;
  categories_en: string;
  categories_fa: string;
  source_url: string;
  retrieved_at: string;
  last_verified_at: string;
  extraction_status: string;
  content_hash: string;
  record_version: number;
  inventory: Array<{
    data_type: string;
    reported_count_label: string;
    safety_policy_applied: string;
  }>;
}

interface Organization {
  id: number;
  name: string;
  native_name: string;
  acronym: string;
  org_type: string;
  description: string;
  linked_articles_count: number;
  linked_entities_count: number;
  source_url: string;
  retrieved_at: string;
}

interface Category {
  id: number;
  slug: string;
  name_en: string;
  name_fa: string;
  description: string;
  article_count: number;
  publication_count: number;
}

interface CollectionJob {
  id: number;
  job_uuid: string;
  job_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_discovered: number;
  processed_count: number;
  new_records_count: number;
  updated_records_count: number;
  skipped_unchanged_count: number;
  blocked_sensitive_count: number;
  failed_count: number;
  checkpoint_data: string;
  error_summary: string | null;
}

interface CollectionHistoryItem {
  id: number;
  job_id: number;
  target_url: string;
  record_type: string;
  http_status: number | null;
  action_taken: string;
  timestamp: string;
  message: string;
}

interface BackupItem {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: string;
  integrity_verified: boolean;
}

interface TrendPoint {
  period: string;
  articles_collected: number;
  catalogues_collected: number;
  records_added: number;
  total_database_growth: number;
}

interface ScheduleState {
  enabled: boolean;
  frequency: string;
  time_utc: string;
  day_of_week: string;
  max_items_per_run: number;
  last_run_at: string;
  next_run_at: string;
  runner_status: string;
}

interface CsvDatasetMeta {
  id: number;
  dataset_name: string;
  original_filename: string;
  headers: string[];
  row_count: number;
  xlsx_export_path?: string;
  retrieved_at?: string;
}

interface CsvRowRecord {
  id: number;
  row_number: number;
  cells: Record<string, string>;
  searchable_text: string;
}

interface ActiveCsvPayload {
  dataset: CsvDatasetMeta | null;
  rows: CsvRowRecord[];
  total_matching_count?: number;
  displayed_count?: number;
  is_subset?: boolean;
  preview_all?: boolean;
  cross_dataset_audit?: boolean;
}

interface OverviewPayload {
  ok: boolean;
  stats: {
    articles_count: number;
    publications_count: number;
    organizations_count: number;
    entities_count: number;
    categories_count: number;
    sources_count: number;
    file_inventory_count: number;
    jobs_count: number;
    changes_count: number;
    last_job: CollectionJob | null;
  };
  trends: TrendPoint[];
  schedule: ScheduleState;
  csv_datasets: CsvDatasetMeta[];
  active_csv: ActiveCsvPayload;
  settings: Record<string, string>;
  articles: Article[];
  publications: Publication[];
  organizations: Organization[];
  categories: Category[];
  tags?: Array<{
    id: number;
    slug: string;
    name: string;
    linked_articles_count: number;
    linked_articles_titles?: string;
  }>;
  sources: Array<Record<string, unknown>>;
  jobs: CollectionJob[];
  history: CollectionHistoryItem[];
  changes: Array<Record<string, unknown>>;
  backups: BackupItem[];
  integrity: { verified: boolean; message: string };
  logs: string[];
  paths: {
    base_dir: string;
    db_path: string;
    backups_dir: string;
    exports_dir: string;
    logs_dir: string;
  };
}

export default function App() {
  const [data, setData] = useState<OverviewPayload | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeNav, setActiveNav] = useState<NavSection>('dashboard');
  const [lang, setLang] = useState<Language>('en');
  const [bannerMessage, setBannerMessage] = useState<{ text: string; type: 'info' | 'error' } | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [storagePathInput, setStoragePathInput] = useState<string>('C:\\WikIranArchive');

  // Responsive sidebar drawer state for smaller window sizes
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  // Application Workflow Modal state (triggers on first launch + accessible via "How to work?" button)
  const [showWorkflowModal, setShowWorkflowModal] = useState<boolean>(() => {
    try {
      return localStorage.getItem('wikiran_workflow_modal_seen_v2') !== 'true';
    } catch {
      return true;
    }
  });

  // Network connectivity state (auto-detects browser online/offline + allows manual offline test toggle)
  const [isOffline, setIsOffline] = useState<boolean>(() =>
    typeof navigator !== 'undefined' ? !navigator.onLine : false
  );

  // Step-by-step live pipeline walkthrough state on Dashboard
  const [activePipelineStep, setActivePipelineStep] = useState<number>(0);
  const [pipelineLog, setPipelineLog] = useState<string | null>(null);

  // Search filters state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterCategory, setFilterCategory] = useState('ALL');
  const [filterOrg, setFilterOrg] = useState('ALL');
  const [filterType, setFilterType] = useState('ALL');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');
  const [searchResults, setSearchResults] = useState<Array<Record<string, unknown>> | null>(null);

  // Selected article reader
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);

  // Confirm restore state
  const [confirmRestorePath, setConfirmRestorePath] = useState<string | null>(null);

  // Scheduled Collection form state
  const [schedEnabled, setSchedEnabled] = useState<boolean>(true);
  const [schedFreq, setSchedFreq] = useState<string>('daily');
  const [schedTime, setSchedTime] = useState<string>('02:00');
  const [schedDay, setSchedDay] = useState<string>('sunday');
  const [schedMaxItems, setSchedMaxItems] = useState<number>(6);

  // CSV-to-Excel Workbench state (including Preview All Matching Records & Cross-Dataset Audit)
  const [selectedCsvId, setSelectedCsvId] = useState<number | null>(null);
  const [csvFilterQuery, setCsvFilterQuery] = useState<string>('');
  const [csvPreviewAll, setCsvPreviewAll] = useState<boolean>(false);
  const [csvCrossDatasetAudit, setCsvCrossDatasetAudit] = useState<boolean>(false);
  const [activeCsvView, setActiveCsvView] = useState<ActiveCsvPayload | null>(null);

  // Export Report Wizard state: allows clerk to choose specific data entities (Articles, Publications, Organizations, Tags)
  const [wizardEntities, setWizardEntities] = useState<
    Array<'articles' | 'publications' | 'organizations' | 'tags'>
  >(['articles', 'publications']);

  const toggleWizardEntity = (entity: 'articles' | 'publications' | 'organizations' | 'tags') => {
    setWizardEntities((prev) =>
      prev.includes(entity) ? prev.filter((item) => item !== entity) : [...prev, entity]
    );
  };

  // Helper to highlight search query terms with a bold yellow background inside summaries and excerpts
  const highlightSearchTerms = (text: string, rawQuery: string): React.ReactNode => {
    if (!text) return '';
    const cleaned = (rawQuery || '')
      .replace(/["*]/g, ' ')
      .split(/\s+/)
      .map((term) => term.trim())
      .filter(
        (term) =>
          term.length > 0 && !['AND', 'OR', 'NOT'].includes(term.toUpperCase())
      );
    if (cleaned.length === 0) return text;

    // Sort longer terms first and escape regex special characters
    const uniqueTerms = Array.from(new Set(cleaned)).sort((a, b) => b.length - a.length);
    const escaped = uniqueTerms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const pattern = new RegExp(`(${escaped.join('|')})`, 'gi');
    const parts = text.split(pattern);

    return parts.map((part, idx) => {
      const isMatch = uniqueTerms.some((term) => part.toLowerCase() === term.toLowerCase());
      if (isMatch) {
        return (
          <mark
            key={idx}
            className="bg-yellow-300 text-slate-950 font-bold px-1 rounded-xs"
          >
            {part}
          </mark>
        );
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };

  // Engineering / Doc viewer
  const [docKey, setDocKey] = useState<string>('reconnaissance');
  const [docContent, setDocContent] = useState<{ filename: string; content: string } | null>(null);
  const [testOutput, setTestOutput] = useState<string | null>(null);

  const t = UI_LABELS[lang];
  const isRtl = lang === 'fa';

  const closeWorkflowModal = () => {
    setShowWorkflowModal(false);
    try {
      localStorage.setItem('wikiran_workflow_modal_seen_v2', 'true');
    } catch {
      // ignore storage errors
    }
  };

  const fetchOverview = useCallback(async () => {
    try {
      const res = await fetch('/api/overview');
      const json: OverviewPayload = await res.json();
      if (json.ok) {
        setData(json);
        const savedLang = json.settings?.ui_language === 'fa' ? 'fa' : 'en';
        setLang(savedLang);
        if (json.settings?.custom_storage_path) {
          setStoragePathInput(json.settings.custom_storage_path);
        } else if (json.paths?.base_dir) {
          setStoragePathInput(json.paths.base_dir);
        }
        if (json.schedule) {
          setSchedEnabled(json.schedule.enabled);
          setSchedFreq(json.schedule.frequency);
          setSchedTime(json.schedule.time_utc);
          setSchedDay(json.schedule.day_of_week);
          setSchedMaxItems(json.schedule.max_items_per_run);
        }
        if (json.active_csv) {
          setActiveCsvView(json.active_csv);
          setSelectedCsvId(json.active_csv.dataset?.id ?? null);
        }
      }
    } catch {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'خطا در ارتباط با موتور محلی پایتون.'
            : 'Could not connect to local Python archive engine.',
        type: 'error',
      });
    } finally {
      setLoading(false);
    }
  }, [lang]);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  useEffect(() => {
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
    document.documentElement.lang = lang;
  }, [isRtl, lang]);

  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const loadDoc = useCallback(async (key: string) => {
    setDocKey(key);
    try {
      const res = await fetch(`/api/docs/${key}`);
      const json = await res.json();
      if (json.ok) {
        setDocContent({ filename: json.filename, content: json.content });
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    if (activeNav === 'help' || activeNav === 'settings') {
      loadDoc(activeNav === 'help' ? (lang === 'fa' ? 'manual_fa' : 'manual_en') : docKey);
    }
  }, [activeNav, lang, docKey, loadDoc]);

  const handleLanguageSwitch = async (nextLang: Language) => {
    setLang(nextLang);
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ui_language: nextLang }),
    });
  };

  const handleSaveStoragePath = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanedPath = storagePathInput.trim() || 'C:\\WikIranArchive';
    setBusyAction('save-storage-path');
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ custom_storage_path: cleanedPath }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `مسیر ذخیره‌سازی اطلاعات با موفقیت روی «${cleanedPath}» تنظیم شد.`
              : `Storage Path updated to "${cleanedPath}". Database, Excel exports, and backups will use this directory.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Toggle between Full Unredacted Archive Mode (strict_sensitive_exclusion = 'false') and Filtered Mode
  const handleToggleArchiveScope = async (enableFullUnredacted: boolean) => {
    setBusyAction('toggle-scope');
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          strict_sensitive_exclusion: enableFullUnredacted ? 'false' : 'true',
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        if (json.active_csv) {
          setActiveCsvView(json.active_csv);
          setSelectedCsvId(json.active_csv.dataset?.id ?? null);
          setCsvPreviewAll(true);
        }
        setBannerMessage({
          text: enableFullUnredacted
            ? lang === 'fa'
              ? 'حالت آرشیو کامل بدون حذفیات فعال شد: مکاتبات (/document/emails/*)، فایل‌ها (/document/files/*) و اسناد بانکی اکنون در جستجو و جدول اکسل در دسترس هستند.'
              : 'Full Unredacted Archive Mode activated: All correspondence (/document/emails/*), raw files (/document/files/*), and banking records are now unlocked and searchable.'
            : lang === 'fa'
            ? 'حالت فیلتر عمومی فعال شد.'
            : 'Switched to Filtered Public Scope mode.',
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Stop active deep spider crawl safely at the current page checkpoint
  const handleStopCrawl = async () => {
    try {
      setPipelineLog(
        lang === 'fa'
          ? 'درخواست توقف ثبت شد: خزنده در حال ذخیره نقطه بازیابی (Checkpoint) در دیتابیس SQLite و توقف ایمن است...'
          : 'Stop requested: Spider is saving a verified checkpoint in SQLite and halting cleanly...'
      );
      await fetch('/api/stop-crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      await fetchOverview();
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'عملیات خزش و دریافت داده با موفقیت متوقف شد. تمام رکوردهای دریافت‌شده تا این لحظه در SQLite ذخیره شدند و نقطه بازیابی (Checkpoint) برای ادامه در آینده ثبت گردید.'
            : 'Crawling stopped safely by user. All records downloaded so far are saved in SQLite with a verified checkpoint (Resume anytime in Collection History).',
        type: 'info',
      });
    } finally {
      setBusyAction(null);
    }
  };

  // Interactive Step-by-Step Pipeline Runner on the Dashboard
  const handleRunVisualPipeline = async () => {
    setBusyAction('pipeline');
    try {
      setActivePipelineStep(1);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۱ از ۴: خزش عمیق (Deep Spider) در robots.txt، نقشه سایت، تمام صفحات مقالات (/search?tabType=articles&page=1..N) و فهرست اسناد (/leaks و /archives)...'
          : 'Step 1 of 4: Deep Spider inspecting robots.txt, sitemap.xml, paginated article feeds (/search?tabType=articles&page=1..N), /leaks & /archives...'
      );
      await new Promise((r) => setTimeout(r, 500));

      setActivePipelineStep(2);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۲ از ۴: دنبال کردن تمام لینک‌های داخلی مانند عنکبوت (Spider) و استخراج مقالات، انتشارات، ایمیل‌ها و فایل‌ها...'
          : 'Step 2 of 4: Spidering internal links across pages and extracting articles, publications, correspondence & files...'
      );
      const res = await fetch('/api/update-archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_items: 12, deep_spider: true }),
      });
      const json = await res.json();

      setActivePipelineStep(3);
      setPipelineLog(
        lang === 'fa'
          ? 'مرحله ۳ از ۴: نرمال‌سازی تاریخ‌ها، محاسبه هش SHA-256 و نمایه‌سازی تمام داده‌ها در موتور جستجوی SQLite FTS5...'
          : 'Step 3 of 4: Normalizing dates, verifying SHA-256 hashes, and indexing all tables & CSV rows in SQLite FTS5...'
      );
      await new Promise((r) => setTimeout(r, 350));

      setActivePipelineStep(4);
      await fetchOverview();
      const status = json?.job?.status;
      const processed = json?.job?.processed_count ?? 0;
      const discovered = json?.job?.total_discovered ?? processed;
      const newAdded = json?.job?.new_records_count ?? 0;
      if (status === 'INTERRUPTED') {
        setPipelineLog(
          lang === 'fa'
            ? `خزش توسط کاربر متوقف شد: ${newAdded} رکورد جدید ذخیره شد (${processed} از ${discovered} لینک بررسی شد).`
            : `Spider crawl stopped at checkpoint: ${newAdded} NEW records saved (${processed} of ${discovered} discovered links processed).`
        );
      } else {
        setPipelineLog(
          lang === 'fa'
            ? `عملیات ۴ مرحله‌ای خزش عمیق کامل شد: ${newAdded} رکورد جدید دانلود شد (${processed} صفحه از ${discovered} لینک کشف‌شده بررسی شد).`
            : `All 4 Pipeline Steps Verified: ${newAdded} NEW records downloaded (${processed} pages processed across ${discovered} spider-discovered links).`
        );
      }
    } finally {
      setBusyAction(null);
    }
  };

  const runUniversalSearchWithQuery = async (
    q: string,
    opts?: { category?: string; org?: string; type?: string; from?: string; to?: string }
  ) => {
    setBusyAction('search');
    const targetCategory = opts?.category ?? filterCategory;
    const targetOrg = opts?.org ?? filterOrg;
    const targetType = opts?.type ?? filterType;
    const targetFrom = opts?.from ?? filterDateFrom;
    const targetTo = opts?.to ?? filterDateTo;

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          category_slug: targetCategory === 'ALL' ? null : targetCategory,
          organization_name: targetOrg === 'ALL' ? null : targetOrg,
          source_type: targetType === 'ALL' ? null : targetType,
          date_from: targetFrom || null,
          date_to: targetTo || null,
        }),
      });
      const json = await res.json();
      if (json.ok) {
        setSearchResults(json.results);
      }
    } catch {
      // Offline fallback over cached local SQLite records if browser network is completely severed
      if (data) {
        const needle = q.trim().toLowerCase();
        const localPool: Array<Record<string, unknown>> = [
          ...data.articles.map((a) => ({
            record_type: 'ARTICLE',
            id: a.id,
            title: a.title,
            short_description: a.summary,
            matched_excerpt: a.editorial_content,
            publication_date: a.publication_date,
            category_en: a.categories_en,
            category_fa: a.categories_fa,
            organizations: a.organizations_list,
            source_url: a.source_url,
            extraction_status: a.extraction_status,
            record_version: a.record_version,
          })),
          ...data.publications.map((p) => ({
            record_type: 'PUBLICATION',
            id: p.id,
            title: p.title,
            short_description: p.description,
            matched_excerpt: p.description,
            publication_date: p.publication_date,
            category_en: p.categories_en,
            category_fa: p.categories_fa,
            organizations: '',
            source_url: p.source_url,
            extraction_status: p.extraction_status,
            record_version: p.record_version,
          })),
          ...(currentCsvRows || []).map((r) => ({
            record_type: 'CSV_ROW',
            id: r.id,
            title: `${currentCsvDataset?.dataset_name || 'CSV'} — Row #${r.row_number}`,
            short_description: r.searchable_text,
            matched_excerpt: r.searchable_text,
            publication_date: '2026-01-01',
            category_en: 'Spreadsheet / CSV Data',
            category_fa: 'داده جدولی اکسل / CSV',
            organizations: '',
            source_url: `local://csv/${currentCsvDataset?.original_filename || 'table.csv'}#row-${r.row_number}`,
            extraction_status: 'INDEXED',
            record_version: 1,
          })),
        ];
        const filtered = localPool.filter((item) => {
          if (targetType !== 'ALL' && item.record_type !== targetType) return false;
          if (!needle) return true;
          const haystack = `${item.title} ${item.short_description} ${item.matched_excerpt} ${item.organizations} ${item.source_url}`.toLowerCase();
          return haystack.includes(needle);
        });
        setSearchResults(filtered);
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    await runUniversalSearchWithQuery(searchQuery);
  };

  const handleUpdateArchive = async (
    simulateInterruptAfter?: number,
    maxItems: number = 12,
    deepSpider: boolean = true
  ) => {
    if (isOffline) {
      setBannerMessage({
        text:
          lang === 'fa'
            ? 'آفلاین (Disconnected): اتصال به اینترنت برقرار نیست. دریافت داده جدید از سرور متوقف است، اما جستجو، مرور و خروجی اکسل از دیتابیس محلی SQLite کاملاً فعال است.'
            : 'Disconnected (Offline Mode): Remote server sync requires internet, but all local SQLite search, browsing, and Excel exports remain 100% functional.',
        type: 'error',
      });
      return;
    }
    setBusyAction('update');
    setBannerMessage(null);
    try {
      const res = await fetch('/api/update-archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_items: maxItems,
          deep_spider: deepSpider,
          simulate_interrupt_after: simulateInterruptAfter,
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok && json.job) {
        const status = json.job.status;
        const newCount = json.job.new_records_count ?? 0;
        const updCount = json.job.updated_records_count ?? 0;
        const procCount = json.job.processed_count ?? 0;
        const discCount = json.job.total_discovered ?? procCount;
        if (status === 'FAILED' || status === 'SUSPENDED') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `خطا در دریافت از سرور (${status}): ${json.job.error_summary || 'خطای شبکه'}`
                : `Server update ${status.toLowerCase()}: ${json.job.error_summary || 'Network error'}`,
            type: 'error',
          });
        } else if (status === 'INTERRUPTED') {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `خزش در نقطه بازیابی متوقف شد (Job #${json.job.id} — ${newCount} رکورد جدید ذخیره شد، ${procCount} از ${discCount} لینک بررسی شد). هر زمان بخواهید می‌توانید از بخش تاریخچه آن را ادامه دهید.`
                : `Spider crawl stopped with verified checkpoint (Job #${json.job.id} — ${newCount} new records saved, ${procCount}/${discCount} links processed). Click Resume anytime in Collection History.`,
            type: 'info',
          });
        } else {
          setBannerMessage({
            text:
              lang === 'fa'
                ? `خزش عمیق (Deep Spider) از سرور wikiran.org تکمیل شد: ${newCount} رکورد جدید دانلود و اضافه شد، ${updCount} رکورد بروزرسانی شد (${procCount} صفحه از ${discCount} لینک کشف‌شده بررسی شد).`
                : `Deep Spider crawl from wikiran.org complete: ${newCount} NEW records downloaded & indexed, ${updCount} updated (${procCount} pages processed out of ${discCount} discovered links).`,
            type: 'info',
          });
        }
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusyAction('schedule-save');
    try {
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: schedEnabled,
          frequency: schedFreq,
          time_utc: schedTime,
          day_of_week: schedDay,
          max_items_per_run: schedMaxItems,
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `تنظیمات زمان‌بندی خودکار ذخیره شد. اجرای بعدی: ${json.schedule.next_run_at}`
              : `Scheduled Collection updated. Next background run: ${json.schedule.next_run_at}`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleTriggerScheduledRunNow = async () => {
    setBusyAction('schedule-run');
    try {
      const res = await fetch('/api/schedule/run-now', { method: 'POST' });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `سرویس زمان‌بندی پس‌زمینه اجرا شد (Job #${json.job?.id}).`
              : `Background scheduled task executed (Job #${json.job?.id}).`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleCsvFilterChange = async (
    datasetId: number | null,
    query: string,
    previewAllFlag: boolean = csvPreviewAll,
    crossAuditFlag: boolean = csvCrossDatasetAudit
  ) => {
    setCsvFilterQuery(query);
    setSelectedCsvId(datasetId);
    setCsvPreviewAll(previewAllFlag);
    setCsvCrossDatasetAudit(crossAuditFlag);
    const res = await fetch('/api/csv/view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dataset_id: datasetId,
        query,
        preview_all: previewAllFlag,
        cross_dataset_audit: crossAuditFlag,
      }),
    });
    const json = await res.json();
    if (json.ok) {
      setActiveCsvView(json.active_csv);
    }
  };

  const handleCsvFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusyAction('csv-upload');
    try {
      const text = await file.text();
      const res = await fetch('/api/csv/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          csv_text: text,
          filename: file.name,
          dataset_name: file.name.replace(/\.csv$/i, ''),
        }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok && json.active_csv?.dataset) {
        setActiveCsvView(json.active_csv);
        setSelectedCsvId(json.active_csv.dataset.id);
        setCsvPreviewAll(true);
        setBannerMessage({
          text:
            lang === 'fa'
              ? `فایل CSV «${file.name}» با موفقیت به جدول اکسل (.xlsx) تبدیل شد و تمام ردیف‌های آن در موتور جستجوی جامع ثبت گردید.`
              : `CSV "${file.name}" converted to Excel (.xlsx) and indexed for universal search.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
      e.target.value = '';
    }
  };

  const handleResumeJob = async (jobId: number) => {
    setBusyAction(`resume-${jobId}`);
    try {
      const res = await fetch('/api/resume-job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({
          text:
            lang === 'fa'
              ? `ادامه عملیات دریافت (#${jobId}) با موفقیت از نقطه ذخیره تکمیل شد.`
              : `Interrupted collection job #${jobId} resumed from checkpoint and completed.`,
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleCreateBackup = async () => {
    setBusyAction('backup');
    try {
      const res = await fetch('/api/backup/create', { method: 'POST' });
      const json = await res.json();
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({ text: json.clerk_message, type: 'info' });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleConfirmRestore = async (backupPath: string) => {
    setBusyAction('restore');
    try {
      const res = await fetch('/api/backup/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: backupPath, confirmed: true }),
      });
      const json = await res.json();
      setConfirmRestorePath(null);
      await fetchOverview();
      if (json.ok) {
        setBannerMessage({ text: json.clerk_message, type: 'info' });
      }
    } finally {
      setBusyAction(null);
    }
  };

  const handleRunTests = async () => {
    setBusyAction('tests');
    try {
      const res = await fetch('/api/tests');
      const json = await res.json();
      setTestOutput(json.output);
    } finally {
      setBusyAction(null);
    }
  };

  const handleRunRecon = async () => {
    setBusyAction('recon');
    try {
      const res = await fetch('/api/reconnaissance', { method: 'POST' });
      const json = await res.json();
      if (json.ok && json.markdown) {
        setDocKey('reconnaissance');
        setDocContent({ filename: 'RECONNAISSANCE_REPORT.md (Live Run)', content: json.markdown });
        setBannerMessage({
          text:
            lang === 'fa'
              ? 'شناسایی فنی وب‌سایت و بررسی مسیرهای مجاز با موفقیت انجام شد.'
              : 'Live website reconnaissance and permitted path analysis completed.',
          type: 'info',
        });
      }
    } finally {
      setBusyAction(null);
    }
  };

  // Distinct Role-Based Color-Coded Navigation Groups (Clerk vs Admin)
  const clerkNavItems: Array<{
    id: NavSection;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    dotClass: string;
  }> = [
    {
      id: 'dashboard',
      label: t.nav_dashboard,
      icon: <LayoutDashboard className="w-4 h-4 text-sky-400 shrink-0" />,
      activeClass: 'bg-sky-600 text-white shadow-xs',
      dotClass: 'bg-sky-400',
    },
    {
      id: 'search',
      label: t.nav_search,
      icon: <Search className="w-4 h-4 text-indigo-400 shrink-0" />,
      activeClass: 'bg-indigo-600 text-white shadow-xs',
      dotClass: 'bg-indigo-400',
    },
    {
      id: 'exports',
      label: t.nav_exports,
      icon: <FileSpreadsheet className="w-4 h-4 text-emerald-400 shrink-0" />,
      activeClass: 'bg-emerald-600 text-white shadow-xs',
      dotClass: 'bg-emerald-400',
    },
    {
      id: 'articles',
      label: t.nav_articles,
      icon: <BookOpen className="w-4 h-4 text-blue-400 shrink-0" />,
      activeClass: 'bg-blue-600 text-white shadow-xs',
      dotClass: 'bg-blue-400',
    },
    {
      id: 'publications',
      label: t.nav_publications,
      icon: <FolderKanban className="w-4 h-4 text-teal-400 shrink-0" />,
      activeClass: 'bg-teal-600 text-white shadow-xs',
      dotClass: 'bg-teal-400',
    },
    {
      id: 'organizations',
      label: t.nav_organizations,
      icon: <Building2 className="w-4 h-4 text-amber-400 shrink-0" />,
      activeClass: 'bg-amber-600 text-white shadow-xs',
      dotClass: 'bg-amber-400',
    },
    {
      id: 'categories',
      label: t.nav_categories,
      icon: <Tags className="w-4 h-4 text-purple-400 shrink-0" />,
      activeClass: 'bg-purple-600 text-white shadow-xs',
      dotClass: 'bg-purple-400',
    },
    {
      id: 'help',
      label: t.nav_help,
      icon: <HelpCircle className="w-4 h-4 text-rose-400 shrink-0" />,
      activeClass: 'bg-rose-600 text-white shadow-xs',
      dotClass: 'bg-rose-400',
    },
  ];

  const adminNavItems: Array<{
    id: NavSection;
    label: string;
    icon: React.ReactNode;
    activeClass: string;
    dotClass: string;
  }> = [
    {
      id: 'history',
      label: t.nav_history,
      icon: <History className="w-4 h-4 text-orange-400 shrink-0" />,
      activeClass: 'bg-orange-600 text-white shadow-xs',
      dotClass: 'bg-orange-400',
    },
    {
      id: 'settings',
      label: t.nav_settings,
      icon: <Settings className="w-4 h-4 text-cyan-400 shrink-0" />,
      activeClass: 'bg-cyan-600 text-white shadow-xs',
      dotClass: 'bg-cyan-400',
    },
  ];

  const allNavItems = [...clerkNavItems, ...adminNavItems];

  if (loading || !data) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-lg p-6 text-center space-y-3">
          <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin mx-auto" />
          <div className="text-base font-semibold text-slate-900">
            Initializing WikIran Archive (SQLite + FTS5)...
          </div>
          <p className="text-xs text-slate-500">
            Verifying normalized SQLite schema, universal FTS5 search index, and CSV-to-Excel workbench.
          </p>
        </div>
      </div>
    );
  }

  const isFullUnredactedMode = data.settings?.strict_sensitive_exclusion === 'false';

  const displayedSearchResults =
    searchResults !== null
      ? searchResults
      : [
          ...data.articles.map((a) => ({
            record_type: 'ARTICLE',
            id: a.id,
            title: a.title,
            short_description: a.summary,
            publication_date: a.publication_date,
            category_en: a.categories_en,
            category_fa: a.categories_fa,
            organizations: a.organizations_list,
            source_url: a.source_url,
            extraction_status: a.extraction_status,
            record_version: a.record_version,
          })),
          ...data.publications.map((p) => ({
            record_type: 'PUBLICATION',
            id: p.id,
            title: p.title,
            short_description: p.description,
            publication_date: p.publication_date,
            category_en: p.categories_en,
            category_fa: p.categories_fa,
            organizations: '',
            source_url: p.source_url,
            extraction_status: p.extraction_status,
            record_version: p.record_version,
          })),
        ];

  const currentCsvState = activeCsvView ?? data.active_csv;
  const currentCsvDataset = currentCsvState?.dataset ?? null;
  const currentCsvRows = currentCsvState?.rows ?? [];
  const totalCsvMatching = currentCsvState?.total_matching_count ?? currentCsvRows.length;
  const displayedCsvCount = currentCsvState?.displayed_count ?? currentCsvRows.length;
  const isCsvSubset = Boolean(currentCsvState?.is_subset);

  return (
    <div dir={isRtl ? 'rtl' : 'ltr'} className="min-h-screen bg-slate-50 text-slate-900 flex relative">
      {/* APPLICATION WORKFLOW MODAL (Triggers on first launch & via "How to work?" button) */}
      {showWorkflowModal && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white border-2 border-indigo-300 rounded-xl max-w-4xl w-full overflow-hidden shadow-xl my-auto">
            <div className="bg-slate-900 text-white px-6 py-5 flex items-start justify-between gap-4 border-b border-slate-800">
              <div className="space-y-1">
                <div className="text-xs font-bold text-sky-400 uppercase tracking-wider">
                  {lang === 'fa' ? 'راهنمای شروع سریع (گام‌به‌گام)' : 'QUICK START WALKTHROUGH · STEP-BY-STEP GUIDE'}
                </div>
                <h2 className="text-lg sm:text-xl font-bold text-white">
                  {t.workflowModalTitle}
                </h2>
                <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                  {t.workflowModalSubtitle}
                </p>
              </div>
              <button
                onClick={closeWorkflowModal}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer shrink-0"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50">
              {/* Walkthrough Step 1: Update Archive (Admin) */}
              <div className="bg-white border border-sky-200 border-t-4 border-t-sky-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-sky-100 text-sky-900">
                      {t.workflowStep1Badge}
                    </span>
                    <RefreshCw className="w-4 h-4 text-sky-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep1Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep1Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    handleUpdateArchive();
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep1Btn}
                </button>
              </div>

              {/* Walkthrough Step 2: Search All Downloaded Data (Clerk) */}
              <div className="bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-900">
                      {t.workflowStep2Badge}
                    </span>
                    <Search className="w-4 h-4 text-indigo-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep2Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep2Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('search');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-indigo-700 hover:bg-indigo-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep2Btn}
                </button>
              </div>

              {/* Walkthrough Step 3: Export & CSV-to-Excel (Clerk) */}
              <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-900">
                      {t.workflowStep3Badge}
                    </span>
                    <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep3Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep3Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('exports');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep3Btn}
                </button>
              </div>

              {/* Walkthrough Step 4: Backup & Schedule (Admin) */}
              <div className="bg-white border border-amber-200 border-t-4 border-t-amber-600 rounded-lg p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                      {t.workflowStep4Badge}
                    </span>
                    <Clock className="w-4 h-4 text-amber-700" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{t.workflowStep4Title}</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">{t.workflowStep4Desc}</p>
                </div>
                <button
                  onClick={() => {
                    closeWorkflowModal();
                    setActiveNav('settings');
                  }}
                  className="w-full py-2 px-3 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-md transition-colors cursor-pointer"
                >
                  {t.workflowStep4Btn}
                </button>
              </div>
            </div>

            <div className="px-6 py-4 bg-white border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-slate-600">
                {lang === 'fa'
                  ? 'هر زمان نیاز به راهنما داشتید، روی دکمه «چگونه کار می‌کند؟» در بالای پیشخوان کلیک کنید.'
                  : 'You can reopen this visual walkthrough anytime via the "How to work?" button on the Dashboard.'}
              </div>
              <button
                onClick={closeWorkflowModal}
                className="px-5 py-2 text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                {t.workflowCloseBtn}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile / Tablet Backdrop Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar Navigation (Responsive Drawer on small screens, Static 264px on lg+) */}
      <aside
        className={`fixed lg:static inset-y-0 ${
          isRtl ? 'right-0' : 'left-0'
        } z-40 w-64 bg-slate-900 text-slate-100 flex flex-col shrink-0 border-e border-slate-800 transition-transform duration-200 ease-in-out ${
          sidebarOpen
            ? 'translate-x-0'
            : isRtl
            ? 'translate-x-full lg:translate-x-0'
            : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="px-5 py-4 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between gap-2">
          <div>
            <div className="text-base font-bold tracking-tight text-white whitespace-nowrap">
              {t.appTitle}
            </div>
            <div className="text-xs text-sky-400 mt-0.5 leading-snug font-medium">
              Windows 11 · SQLite FTS5
            </div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Close navigation menu"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
          {/* Group 1: Clerk Tasks (Emerald / Indigo / Blue Color-Coded Group) */}
          <div className="space-y-1">
            <div className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center justify-between">
              <span>{t.sidebarClerkGroup}</span>
            </div>
            {clerkNavItems.map((item) => {
              const active = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveNav(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs sm:text-sm font-medium rounded-md transition-colors cursor-pointer ${
                    active
                      ? item.activeClass
                      : 'text-slate-300 hover:bg-slate-800/90 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.icon}
                    <span className="truncate">{item.label}</span>
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      active ? 'bg-white' : item.dotClass
                    }`}
                  />
                </button>
              );
            })}
          </div>

          {/* Group 2: Admin Tasks (Amber / Cyan Color-Coded Group) */}
          <div className="space-y-1 pt-2 border-t border-slate-800">
            <div className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-400 flex items-center justify-between">
              <span>{t.sidebarAdminGroup}</span>
            </div>
            {adminNavItems.map((item) => {
              const active = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveNav(item.id);
                    setSidebarOpen(false);
                  }}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-2 text-xs sm:text-sm font-medium rounded-md transition-colors cursor-pointer ${
                    active
                      ? item.activeClass
                      : 'text-slate-300 hover:bg-slate-800/90 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.icon}
                    <span className="truncate">{item.label}</span>
                  </div>
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      active ? 'bg-white' : item.dotClass
                    }`}
                  />
                </button>
              );
            })}
          </div>
        </nav>

        {/* Sidebar Footer: Language & Mode Switch */}
        <div className="p-4 border-t border-slate-800 space-y-3 bg-slate-950/40">
          <button
            onClick={() => {
              setShowWorkflowModal(true);
              setSidebarOpen(false);
            }}
            className="w-full py-2 px-3 text-xs font-bold text-sky-950 bg-sky-400 hover:bg-sky-300 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>{t.howToWorkBtn}</span>
          </button>

          <div className="flex items-center gap-1 p-1 bg-slate-800 rounded-md">
            <button
              onClick={() => handleLanguageSwitch('en')}
              className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer ${
                lang === 'en' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              English (LTR)
            </button>
            <button
              onClick={() => handleLanguageSwitch('fa')}
              className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded transition-colors whitespace-nowrap cursor-pointer ${
                lang === 'fa' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              فارسی (RTL)
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area (Responsive width & padding) */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar Contract: Responsive Zone 1 Brand/Menu — Zone 2 Quick Universal Search — Zone 3 Primary CTA */}
        <header className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 lg:px-8 py-3.5 bg-white border-b border-slate-200">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-md border border-slate-200 text-slate-700 hover:bg-slate-100 cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="text-sm sm:text-base font-bold text-slate-900 truncate">
              {t.appTitle} — {allNavItems.find((n) => n.id === activeNav)?.label}
            </div>
          </div>

          {/* Global Universal Search Bar in Header */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setActiveNav('search');
              runUniversalSearchWithQuery(searchQuery);
            }}
            className="flex items-center gap-2 flex-1 max-w-md min-w-[220px]"
          >
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={
                  lang === 'fa'
                    ? 'جستجوی سریع در تمام داده‌های دانلودشده...'
                    : 'Quick search across all downloaded data...'
                }
                className="w-full px-3 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-md focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'جستجو' : 'Search'}
            </button>
          </form>

          <div className="flex items-center gap-2 shrink-0">
            {/* Network Status Indicator (Turns Red when Offline + Clickable to test Offline Mode) */}
            <button
              type="button"
              onClick={() => setIsOffline((prev) => !prev)}
              title={
                lang === 'fa'
                  ? 'وضعیت اتصال شبکه (برای شبیه‌سازی حالت آفلاین کلیک کنید)'
                  : 'Network Status Indicator (Click to toggle Offline / Online simulation)'
              }
              className={`px-3 py-2 text-xs font-bold rounded-md border transition-colors whitespace-nowrap inline-flex items-center gap-1.5 cursor-pointer shadow-xs ${
                isOffline
                  ? 'bg-red-600 text-white border-red-700 hover:bg-red-700'
                  : 'bg-emerald-50 text-emerald-900 border-emerald-300 hover:bg-emerald-100'
              }`}
            >
              {isOffline ? (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-white shrink-0" />
                  <span>
                    {lang === 'fa' ? 'آفلاین / قطع ارتباط (Disconnected)' : 'Disconnected (Offline)'}
                  </span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-600 shrink-0" />
                  <Wifi className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                  <span>{lang === 'fa' ? 'آنلاین (متصل)' : 'Online'}</span>
                </>
              )}
            </button>
            <button
              onClick={() => setShowWorkflowModal(true)}
              className="px-3 py-2 text-xs font-bold text-indigo-950 bg-indigo-100 border border-indigo-300 rounded-md hover:bg-indigo-200 transition-colors whitespace-nowrap inline-flex items-center gap-1.5 cursor-pointer"
            >
              <HelpCircle className="w-3.5 h-3.5 text-indigo-700" />
              <span>{t.howToWorkBtn}</span>
            </button>
            <a
              href="/api/export/xlsx"
              className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-700 rounded-md hover:bg-emerald-800 transition-colors whitespace-nowrap inline-flex items-center gap-1.5 shadow-xs"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t.actionExportExcel}</span>
            </a>
          </div>
        </header>

        {/* Disconnected Banner (Appears when App is Offline while Local SQLite Search, Browsing & Export remain 100% functional) */}
        {isOffline && (
          <div className="bg-red-600 text-white border-b border-red-700 px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs shadow-xs">
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <WifiOff className="w-4 h-4 text-white shrink-0" />
              <span className="font-bold">
                {lang === 'fa'
                  ? 'قطع ارتباط با شبکه (Disconnected) — حالت آفلاین فعال است: دریافت داده جدید از سرور متوقف است، اما تمام امکانات جستجوی محلی، مرور مقالات و خروجی‌های اکسل از دیتابیس محلی SQLite کاملاً فعال هستند.'
                  : 'Disconnected — Offline Mode Active: Internet connection is unavailable. Server sync is paused, while all local SQLite FTS5 search, browsing, CSV-to-Excel workbench, and Excel/CSV/JSON exports remain 100% functional.'}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setIsOffline(false)}
              className="px-2.5 py-1 text-xs font-bold bg-white text-red-700 rounded hover:bg-red-50 transition-colors shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'بازگشت به حالت آنلاین' : 'Reconnect Online'}
            </button>
          </div>
        )}

        {/* Configurable Archive Scope Banner (Full Unredacted Mode vs Filtered Mode) */}
        <div
          className={`border-b px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs ${
            isFullUnredactedMode
              ? 'bg-indigo-50/90 border-indigo-200 text-indigo-950'
              : 'bg-amber-50/90 border-amber-200 text-amber-950'
          }`}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {isFullUnredactedMode ? (
              <Unlock className="w-4 h-4 text-indigo-700 shrink-0" />
            ) : (
              <Lock className="w-4 h-4 text-amber-700 shrink-0" />
            )}
            <span className="font-medium">
              {isFullUnredactedMode ? t.unredactedNotice : t.safetyNotice}
            </span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => handleToggleArchiveScope(!isFullUnredactedMode)}
              disabled={busyAction === 'toggle-scope'}
              className={`px-3 py-1 rounded font-semibold transition-colors cursor-pointer ${
                isFullUnredactedMode
                  ? 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100'
                  : 'bg-indigo-700 text-white hover:bg-indigo-800'
              }`}
            >
              {isFullUnredactedMode ? t.switchToFilteredModeBtn : t.switchToFullModeBtn}
            </button>
          </div>
        </div>

        {/* Friendly Clerk Notification Banner */}
        {bannerMessage && (
          <div
            className={`px-4 sm:px-6 lg:px-8 py-3 border-b flex items-center justify-between gap-3 text-xs sm:text-sm ${
              bannerMessage.type === 'error'
                ? 'bg-red-50 border-red-200 text-red-900'
                : 'bg-emerald-50 border-emerald-200 text-emerald-900'
            }`}
          >
            <div className="flex items-center gap-2">
              {bannerMessage.type === 'error' ? (
                <AlertTriangle className="w-4 h-4 text-red-700 shrink-0" />
              ) : (
                <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              )}
              <span className="font-medium">{bannerMessage.text}</span>
            </div>
            <button
              onClick={() => setBannerMessage(null)}
              className="text-xs underline font-semibold px-2 py-1 shrink-0 cursor-pointer"
            >
              {lang === 'fa' ? 'بستن' : 'Dismiss'}
            </button>
          </div>
        )}

        {/* Viewport Content (Responsive padding & container) */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 sm:space-y-8">
          {/* 1. DASHBOARD */}
          {activeNav === 'dashboard' && (
            <div className="space-y-6 sm:space-y-8">
              {/* HERO SECTION: HOW THIS APP WORKS + "How to work?" Modal Trigger */}
              <section className="bg-white border border-indigo-200 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 px-5 sm:px-6 py-5 text-white flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-sky-400 tracking-wide">
                      {lang === 'fa'
                        ? 'شروع سریع و راهنمای عملیاتی گام‌به‌گام'
                        : 'START HERE · INTERACTIVE OPERATIONAL WORKFLOW'}
                    </div>
                    <h1 className="text-base sm:text-lg md:text-xl font-bold text-white">
                      {t.howItWorksTitle}
                    </h1>
                    <p className="text-xs text-slate-300 max-w-3xl">{t.howItWorksSubtitle}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                    <button
                      onClick={() => setShowWorkflowModal(true)}
                      className="px-4 py-2.5 text-xs font-bold text-slate-950 bg-amber-400 hover:bg-amber-300 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer"
                    >
                      <HelpCircle className="w-4 h-4" />
                      <span>{t.howToWorkBtn}</span>
                    </button>
                    <button
                      onClick={handleRunVisualPipeline}
                      disabled={busyAction === 'pipeline' || busyAction === 'update'}
                      className="px-4 py-2.5 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer disabled:opacity-60"
                    >
                      <Play className="w-4 h-4" />
                      <span>{t.pipelineRunBtn}</span>
                    </button>
                    {(busyAction === 'pipeline' || busyAction === 'update') && (
                      <button
                        type="button"
                        onClick={handleStopCrawl}
                        className="px-4 py-2.5 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer shadow-xs"
                      >
                        <Square className="w-3.5 h-3.5 fill-current" />
                        <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Crawling'}</span>
                      </button>
                    )}
                  </div>
                </div>

                {pipelineLog && (
                  <div className="px-5 sm:px-6 py-3 bg-sky-50 border-b border-sky-200 text-xs font-semibold text-sky-950 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <RefreshCw
                        className={`w-4 h-4 text-sky-700 shrink-0 ${
                          busyAction === 'pipeline' || busyAction === 'update' ? 'animate-spin' : ''
                        }`}
                      />
                      <span>{pipelineLog}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      {(busyAction === 'pipeline' || busyAction === 'update') && (
                        <button
                          type="button"
                          onClick={handleStopCrawl}
                          className="px-2.5 py-1 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded inline-flex items-center gap-1.5 cursor-pointer"
                        >
                          <Square className="w-3 h-3 fill-current" />
                          <span>{lang === 'fa' ? 'توقف عملیات (Stop)' : 'Stop'}</span>
                        </button>
                      )}
                      <span className="font-mono-tabular text-sky-800">
                        Step {activePipelineStep}/4
                      </span>
                    </div>
                  </div>
                )}

                {/* 4 Color-Distinguished Operational Steps */}
                <div className="p-4 sm:p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Step 1: Sky Blue — Lookup Server Updates (Deep Spider Crawler) */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-sky-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 1
                        ? 'bg-sky-100/80 border-sky-500'
                        : 'bg-sky-50/60 border-sky-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sky-900">
                        <span className="text-sm font-bold">{t.step1Title}</span>
                        <Globe className="w-4 h-4 text-sky-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step1Desc}</p>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleUpdateArchive(undefined, 12, true)}
                          disabled={busyAction === 'update' || busyAction === 'pipeline'}
                          className="flex-1 py-2 px-2.5 text-xs font-semibold text-white bg-sky-700 hover:bg-sky-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${
                              busyAction === 'update' ? 'animate-spin' : ''
                            }`}
                          />
                          <span>{t.step1Action}</span>
                        </button>
                        <button
                          type="button"
                          onClick={handleStopCrawl}
                          title={
                            lang === 'fa'
                              ? 'توقف خزش و ذخیره نقطه بازیابی (Stop)'
                              : 'Stop spider crawling & save checkpoint'
                          }
                          className={`py-2 px-2.5 text-xs font-bold rounded-md transition-colors inline-flex items-center justify-center gap-1 cursor-pointer shrink-0 ${
                            busyAction === 'update' || busyAction === 'pipeline'
                              ? 'bg-red-600 text-white hover:bg-red-700 shadow-xs'
                              : 'bg-red-100 text-red-800 border border-red-300 hover:bg-red-200'
                          }`}
                        >
                          <Square className="w-3 h-3 fill-current" />
                          <span>{lang === 'fa' ? 'توقف' : 'Stop'}</span>
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleUpdateArchive(undefined, 0, true)}
                        disabled={busyAction === 'update' || busyAction === 'pipeline'}
                        className="w-full py-1.5 px-2.5 text-[11px] font-bold text-sky-950 bg-white hover:bg-sky-100 border border-sky-300 rounded-md transition-colors inline-flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                      >
                        <Globe className="w-3 h-3 text-sky-700" />
                        <span>
                          {lang === 'fa'
                            ? 'خزش عنکبوتی کامل (تمام صفحات تا صفحه آخر)'
                            : 'Deep Spider Crawl (All Pages & Links to End)'}
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Step 2: Teal — Download & Extract Records */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-teal-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 2
                        ? 'bg-teal-100/80 border-teal-500'
                        : 'bg-teal-50/60 border-teal-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-teal-950">
                        <span className="text-sm font-bold">{t.step2Title}</span>
                        <ShieldCheck className="w-4 h-4 text-teal-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step2Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('history')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <History className="w-3.5 h-3.5" />
                      <span>{t.step2Action}</span>
                    </button>
                  </div>

                  {/* Step 3: Indigo — Universal SQLite & FTS5 Search */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-indigo-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 3
                        ? 'bg-indigo-100/80 border-indigo-500'
                        : 'bg-indigo-50/60 border-indigo-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-indigo-950">
                        <span className="text-sm font-bold">{t.step3Title}</span>
                        <Search className="w-4 h-4 text-indigo-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step3Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('search')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-indigo-700 hover:bg-indigo-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Search className="w-3.5 h-3.5" />
                      <span>{t.step3Action}</span>
                    </button>
                  </div>

                  {/* Step 4: Emerald — CSV-to-Excel & Backup */}
                  <div
                    className={`rounded-lg p-4 border border-t-4 border-t-emerald-600 transition-colors flex flex-col justify-between space-y-4 ${
                      activePipelineStep === 4
                        ? 'bg-emerald-100/80 border-emerald-500'
                        : 'bg-emerald-50/60 border-emerald-200'
                    }`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-emerald-950">
                        <span className="text-sm font-bold">{t.step4Title}</span>
                        <FileSpreadsheet className="w-4 h-4 text-emerald-700 shrink-0" />
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed">{t.step4Desc}</p>
                    </div>
                    <button
                      onClick={() => setActiveNav('exports')}
                      className="w-full py-2 px-3 text-xs font-semibold text-white bg-emerald-700 hover:bg-emerald-800 rounded-md transition-colors inline-flex items-center justify-center gap-1.5 cursor-pointer"
                    >
                      <Table className="w-3.5 h-3.5" />
                      <span>{t.step4Action}</span>
                    </button>
                  </div>
                </div>
              </section>

              {/* QUICK ACTIONS */}
              <section className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-base font-bold text-slate-900">{t.quickActionsTitle}</h2>
                  {(busyAction === 'update' || busyAction === 'pipeline') && (
                    <button
                      type="button"
                      onClick={handleStopCrawl}
                      className="px-3 py-1.5 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-md inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                    >
                      <Square className="w-3 h-3 fill-current" />
                      <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Active Spider Crawl'}</span>
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {/* Task 1: Universal Search */}
                  <button
                    onClick={() => setActiveNav('search')}
                    className="flex flex-col justify-between p-4 bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg hover:bg-indigo-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-100 text-indigo-900">
                        SQLite FTS5
                      </span>
                      <Search className="w-4 h-4 text-indigo-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionSearch}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Articles + Emails + Files + CSV Rows
                      </div>
                    </div>
                  </button>

                  {/* Task 2: CSV-to-Excel Workbench */}
                  <button
                    onClick={() => setActiveNav('exports')}
                    className="flex flex-col justify-between p-4 bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg hover:bg-emerald-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-100 text-emerald-900">
                        Excel (.xlsx)
                      </span>
                      <Table className="w-4 h-4 text-emerald-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionCsvWorkbench}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Preview All Matching Records (.xlsx)
                      </div>
                    </div>
                  </button>

                  {/* Task 3: Browse Articles */}
                  <button
                    onClick={() => setActiveNav('articles')}
                    className="flex flex-col justify-between p-4 bg-white border border-blue-200 border-t-4 border-t-blue-600 rounded-lg hover:bg-blue-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-100 text-blue-900">
                        Articles
                      </span>
                      <BookOpen className="w-4 h-4 text-blue-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {t.actionBrowseArticles}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        {data.stats.articles_count} Verified Editorial Reports
                      </div>
                    </div>
                  </button>

                  {/* Task 4: Browse Catalogue */}
                  <button
                    onClick={() => setActiveNav('publications')}
                    className="flex flex-col justify-between p-4 bg-white border border-teal-200 border-t-4 border-t-teal-600 rounded-lg hover:bg-teal-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-teal-100 text-teal-900">
                        Catalogues
                      </span>
                      <FolderKanban className="w-4 h-4 text-teal-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {t.actionBrowseCatalogue}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        {data.stats.publications_count} Publication Catalogues
                      </div>
                    </div>
                  </button>

                  {/* Task 5: Deep Spider Update Archive */}
                  <button
                    onClick={() => handleUpdateArchive(undefined, 12, true)}
                    disabled={busyAction === 'update'}
                    className="flex flex-col justify-between p-4 bg-white border border-amber-300 border-t-4 border-t-amber-600 rounded-lg hover:bg-amber-50/50 transition-colors text-start disabled:opacity-50 cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-100 text-amber-950">
                        Deep Spider
                      </span>
                      <RefreshCw
                        className={`w-4 h-4 text-amber-700 shrink-0 ${
                          busyAction === 'update' ? 'animate-spin' : ''
                        }`}
                      />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {t.actionUpdateArchive}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Multi-Page Spider Discovery & Sync
                      </div>
                    </div>
                  </button>

                  {/* Admin Task 2: Create SQLite Backup */}
                  <button
                    onClick={handleCreateBackup}
                    disabled={busyAction === 'backup'}
                    className="flex flex-col justify-between p-4 bg-white border border-purple-300 border-t-4 border-t-purple-600 rounded-lg hover:bg-purple-50/50 transition-colors text-start disabled:opacity-50 cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-purple-100 text-purple-950">
                        {t.adminBadge}
                      </span>
                      <HardDriveDownload className="w-4 h-4 text-purple-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionCreateBackup}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Verified SQLite Snapshot ({data.backups.length} saved)
                      </div>
                    </div>
                  </button>

                  {/* Admin Task 3: Scheduled Auto-Sync */}
                  <button
                    onClick={() => setActiveNav('settings')}
                    className="flex flex-col justify-between p-4 bg-white border border-cyan-300 border-t-4 border-t-cyan-600 rounded-lg hover:bg-cyan-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-100 text-cyan-950">
                        {t.adminBadge}
                      </span>
                      <Clock className="w-4 h-4 text-cyan-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">
                        {lang === 'fa' ? 'زمان‌بندی خودکار دریافت' : 'Scheduled Auto-Sync'}
                      </div>
                      <div className="text-xs text-slate-600 mt-0.5 font-mono-tabular">
                        {data.schedule?.frequency} @ {data.schedule?.time_utc} UTC
                      </div>
                    </div>
                  </button>

                  {/* Clerk / All Task 4: Open Visual Workflow Modal */}
                  <button
                    onClick={() => setShowWorkflowModal(true)}
                    className="flex flex-col justify-between p-4 bg-white border border-rose-200 border-t-4 border-t-rose-600 rounded-lg hover:bg-rose-50/50 transition-colors text-start cursor-pointer space-y-3 shadow-2xs"
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-100 text-rose-900">
                        {t.clerkBadge}
                      </span>
                      <HelpCircle className="w-4 h-4 text-rose-700 shrink-0" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">{t.actionHelp}</div>
                      <div className="text-xs text-slate-600 mt-0.5">
                        Step-by-Step Visual Walkthrough
                      </div>
                    </div>
                  </button>
                </div>
              </section>

              {/* Color-Distinguished KPI Metrics Strip */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white border border-blue-200 border-t-4 border-t-blue-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-blue-800">{t.statArticles}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.articles_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    /document/articles/* · Verified
                  </div>
                </div>
                <div className="bg-white border border-teal-200 border-t-4 border-t-teal-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-teal-800">{t.statPublications}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.publications_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    /leaks & /archives · Indexed
                  </div>
                </div>
                <div className="bg-white border border-amber-200 border-t-4 border-t-amber-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-amber-800">{t.statOrganizations}</div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.stats.organizations_count}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {data.stats.entities_count} Entities Linked
                  </div>
                </div>
                <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-5">
                  <div className="text-xs font-semibold text-emerald-800">
                    {lang === 'fa'
                      ? 'فایل‌های CSV و دفاتر اسناد/ایمیل‌ها'
                      : 'Indexed CSV & Ledger Spreadsheets'}
                  </div>
                  <div className="text-2xl font-bold text-slate-900 font-mono-tabular mt-1">
                    {data.csv_datasets?.length || 2}
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {(data.csv_datasets || []).reduce((acc, d) => acc + d.row_count, 0)} Rows Searchable
                  </div>
                </div>
              </div>

              {/* RECHARTS VISUALIZATION SECTION: Collection Trends & Database Growth */}
              <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-6 space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{t.chartsTitle}</h2>
                    <p className="text-xs text-slate-500">{t.chartsSubtitle}</p>
                  </div>
                  <div className="text-xs font-mono-tabular text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-md border border-indigo-200">
                    Scheduled Auto-Update: {data.schedule?.frequency?.toUpperCase()} @{' '}
                    {data.schedule?.time_utc} UTC
                  </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Chart 1: BarChart of Articles & Catalogues Collected per Period */}
                  <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
                    <div className="text-xs font-semibold text-slate-700 mb-3">
                      {t.chartArticlesLabel}
                    </div>
                    <div className="h-64 w-full" dir="ltr">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data.trends || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                          <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#475569' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#475569' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#FFFFFF',
                              borderColor: '#CBD5E1',
                              fontSize: '12px',
                              borderRadius: '6px',
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: '12px' }} />
                          <Bar
                            dataKey="articles_collected"
                            name={lang === 'fa' ? 'مقالات' : 'Articles'}
                            fill="#2563EB"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="catalogues_collected"
                            name={lang === 'fa' ? 'فهرست انتشارات' : 'Catalogues'}
                            fill="#0D9488"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Chart 2: AreaChart of Cumulative Database Growth */}
                  <div className="border border-slate-200 rounded-lg p-4 bg-slate-50/50">
                    <div className="text-xs font-semibold text-slate-700 mb-3">
                      {t.chartGrowthLabel}
                    </div>
                    <div className="h-64 w-full" dir="ltr">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data.trends || []}>
                          <defs>
                            <linearGradient id="growthGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.35} />
                              <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                          <XAxis dataKey="period" tick={{ fontSize: 11, fill: '#475569' }} />
                          <YAxis tick={{ fontSize: 11, fill: '#475569' }} />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: '#FFFFFF',
                              borderColor: '#CBD5E1',
                              fontSize: '12px',
                              borderRadius: '6px',
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: '12px' }} />
                          <Area
                            type="monotone"
                            dataKey="total_database_growth"
                            name={lang === 'fa' ? 'کل رکوردهای آرشیو' : 'Total Archive Records'}
                            stroke="#4F46E5"
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill="url(#growthGradient)"
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          )}

          {/* 2. UNIVERSAL SEARCH ARCHIVE (Checks ALL Downloaded Data: Articles, Publications, Emails, Files, Banking IBANs, CSV Rows, Entities) */}
          {activeNav === 'search' && (
            <div className="space-y-6">
              <form
                onSubmit={handleSearch}
                className="bg-white border-2 border-indigo-200 rounded-xl p-4 sm:p-6 space-y-4 shadow-2xs"
              >
                <div className="flex flex-col md:flex-row gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t.searchPlaceholder}
                    className="flex-1 px-3.5 py-2.5 text-sm border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  />
                  <button
                    type="submit"
                    disabled={busyAction === 'search'}
                    className="px-5 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-md hover:bg-indigo-700 transition-colors whitespace-nowrap cursor-pointer"
                  >
                    {t.btnSearch}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery('');
                      setFilterCategory('ALL');
                      setFilterOrg('ALL');
                      setFilterType('ALL');
                      setFilterDateFrom('');
                      setFilterDateTo('');
                      setSearchResults(null);
                    }}
                    className="px-4 py-2.5 text-sm font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors whitespace-nowrap cursor-pointer"
                  >
                    {t.btnReset}
                  </button>
                </div>

                {/* Instant Sample Deep-Search Chips (Emails, Banking IBANs, Files, Companies) */}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  <span className="text-xs font-semibold text-slate-500">
                    {lang === 'fa'
                      ? 'نمونه جستجو در کل داده‌های دانلودشده:'
                      : 'Try searching across all downloaded data:'}
                  </span>
                  {[
                    { label: 'settlements@rahbar (Email)', query: 'settlements@rahbar' },
                    { label: 'AE070331234567890123456 (IBAN)', query: 'AE070331234567890123456' },
                    { label: '/document/emails/ (Emails)', query: '/document/emails/' },
                    { label: 'SWIFT MT103 (Banking File)', query: 'SWIFT MT103' },
                    { label: 'Sahara Thunder', query: 'Sahara Thunder' },
                    { label: 'MODAFL', query: 'MODAFL' },
                  ].map((chip) => (
                    <button
                      key={chip.query}
                      type="button"
                      onClick={() => {
                        setSearchQuery(chip.query);
                        setFilterType('ALL');
                        runUniversalSearchWithQuery(chip.query, { type: 'ALL' });
                      }}
                      className="px-2.5 py-1 text-xs font-mono-tabular bg-indigo-50 text-indigo-800 border border-indigo-200 rounded hover:bg-indigo-100 transition-colors cursor-pointer"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-2">
                  <select
                    value={filterCategory}
                    onChange={(e) => setFilterCategory(e.target.value)}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                  >
                    <option value="ALL">{t.filterCategory}</option>
                    {data.categories.map((c) => (
                      <option key={c.slug} value={c.slug}>
                        {isRtl ? c.name_fa : c.name_en}
                      </option>
                    ))}
                  </select>

                  <select
                    value={filterOrg}
                    onChange={(e) => setFilterOrg(e.target.value)}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                  >
                    <option value="ALL">{t.filterOrganization}</option>
                    {data.organizations.map((o) => (
                      <option key={o.id} value={o.acronym || o.name}>
                        {o.name}
                      </option>
                    ))}
                  </select>

                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-semibold text-indigo-950"
                  >
                    <option value="ALL">{t.filterSourceType}</option>
                    <option value="ARTICLE">Articles (/document/articles/*)</option>
                    <option value="PUBLICATION">Publication Catalogues (/leak/*)</option>
                    <option value="CSV_ROW">
                      CSV / Excel Rows (Emails, Banking Ledgers & Tables)
                    </option>
                    <option value="FILE_INVENTORY">File & Document Inventory</option>
                    <option value="ENTITY">Organizations & Entities</option>
                  </select>

                  <input
                    type="date"
                    value={filterDateFrom}
                    onChange={(e) => setFilterDateFrom(e.target.value)}
                    aria-label={t.filterDateFrom}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                  />

                  <input
                    type="date"
                    value={filterDateTo}
                    onChange={(e) => setFilterDateTo(e.target.value)}
                    aria-label={t.filterDateTo}
                    className="px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                  />
                </div>
              </form>

              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-4 sm:px-6 py-3 bg-indigo-50/70 border-b border-indigo-100 flex flex-wrap items-center justify-between gap-2 text-xs text-indigo-950 font-medium">
                  <span>
                    {lang === 'fa'
                      ? `تعداد نتایج یافت‌شده در کل داده‌های دانلودشده: ${displayedSearchResults.length}`
                      : `Showing ${displayedSearchResults.length} matching records across all downloaded archive tables`}
                  </span>
                  <span className="font-mono-tabular">
                    fts_archive JOIN (articles, publications, csv_row_content, file_metadata)
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/60 text-xs text-slate-500">
                        <th className="py-3 px-4 sm:px-6 text-start font-medium">{t.colTitle}</th>
                        <th className="py-3 px-4 text-start font-medium">{t.colDate}</th>
                        <th className="py-3 px-4 text-start font-medium">{t.colCategory}</th>
                        <th className="py-3 px-4 sm:px-6 text-start font-medium">{t.colSource}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {displayedSearchResults.map((row, idx) => {
                        const summaryText = String(row.short_description || '');
                        const excerptText = String(
                          (row as Record<string, unknown>).matched_excerpt || ''
                        );
                        const showDistinctExcerpt =
                          Boolean(searchQuery.trim()) &&
                          Boolean(excerptText) &&
                          excerptText !== summaryText;

                        return (
                          <tr
                            key={`${row.record_type}-${row.id}-${idx}`}
                            className="hover:bg-slate-50 transition-colors"
                          >
                            <td className="py-3.5 px-4 sm:px-6 space-y-1.5">
                              <div className="font-semibold text-slate-900">
                                {highlightSearchTerms(String(row.title || ''), searchQuery)}
                              </div>
                              <div className="text-xs text-slate-700 leading-relaxed">
                                {highlightSearchTerms(summaryText, searchQuery)}
                              </div>
                              {showDistinctExcerpt && (
                                <div className="text-xs text-slate-800 bg-amber-50/80 border-s-2 border-amber-400 ps-2.5 py-1 rounded-e leading-relaxed">
                                  <span className="font-semibold text-slate-600 me-1">
                                    {lang === 'fa' ? 'گزیده متن منطبق:' : 'Matched Excerpt:'}
                                  </span>
                                  {highlightSearchTerms(excerptText.slice(0, 320), searchQuery)}
                                </div>
                              )}
                              <div className="text-xs text-indigo-700 font-semibold">
                                <span>{String(row.record_type || '')}</span>
                                {row.organizations ? (
                                  <>
                                    <span aria-hidden="true"> · </span>
                                    <span>
                                      {highlightSearchTerms(
                                        String(row.organizations),
                                        searchQuery
                                      )}
                                    </span>
                                  </>
                                ) : null}
                              </div>
                            </td>
                            <td className="py-3.5 px-4 font-mono-tabular text-xs text-slate-700 whitespace-nowrap">
                              {String(row.publication_date || '')}
                            </td>
                            <td className="py-3.5 px-4 text-xs text-slate-700">
                              {highlightSearchTerms(
                                String(isRtl ? row.category_fa : row.category_en),
                                searchQuery
                              )}
                            </td>
                            <td className="py-3.5 px-4 sm:px-6 text-xs">
                              <a
                                href={String(row.source_url || '#')}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-700 hover:text-indigo-950 underline inline-flex items-center gap-1 font-mono-tabular break-all"
                              >
                                <span>
                                  {highlightSearchTerms(
                                    String(row.source_url || '').replace('https://wikiran.org', ''),
                                    searchQuery
                                  )}
                                </span>
                                <ExternalLink className="w-3 h-3 shrink-0" />
                              </a>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 3. ARTICLES */}
          {activeNav === 'articles' && (
            <div className="space-y-6">
              {selectedArticle && (
                <div className="bg-white border border-blue-300 rounded-lg p-4 sm:p-6 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="text-xs text-blue-700 font-medium">
                        <span>{selectedArticle.subtitle}</span>
                        <span aria-hidden="true"> · </span>
                        <span className="font-mono-tabular">
                          {selectedArticle.publication_date}
                        </span>
                        <span aria-hidden="true"> · </span>
                        <span>{selectedArticle.author}</span>
                      </div>
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                        {selectedArticle.title}
                      </h2>
                    </div>
                    <button
                      onClick={() => setSelectedArticle(null)}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-100 rounded hover:bg-slate-200 cursor-pointer"
                    >
                      {lang === 'fa' ? 'بستن متن کامل' : 'Close Reader'}
                    </button>
                  </div>
                  <p className="text-sm text-slate-800 leading-relaxed whitespace-pre-line">
                    {selectedArticle.editorial_content}
                  </p>
                  <div className="pt-3 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
                    <div>
                      <span>Organizations: {selectedArticle.organizations_list || 'N/A'}</span>
                      <span aria-hidden="true"> · </span>
                      <span>Tags: {selectedArticle.tags_list || 'N/A'}</span>
                    </div>
                    <div className="font-mono-tabular">
                      SHA-256: {selectedArticle.content_hash.slice(0, 16)}… · v
                      {selectedArticle.record_version}
                    </div>
                  </div>
                </div>
              )}

              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 bg-blue-50/60 text-xs text-blue-950">
                        <th className="py-3 px-4 sm:px-6 text-start font-semibold">{t.colTitle}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colDate}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colCategory}</th>
                        <th className="py-3 px-4 text-start font-semibold">{t.colVersion}</th>
                        <th className="py-3 px-4 sm:px-6 text-start font-semibold">
                          {t.colSource}
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.articles.map((art) => (
                        <tr key={art.id} className="hover:bg-blue-50/30 transition-colors">
                          <td className="py-4 px-4 sm:px-6 space-y-1">
                            <button
                              onClick={() => setSelectedArticle(art)}
                              className="font-semibold text-blue-900 hover:underline text-start cursor-pointer"
                            >
                              {art.title}
                            </button>
                            <p className="text-xs text-slate-600">{art.summary}</p>
                            <div className="text-xs text-slate-500">
                              <span>{art.author}</span>
                              <span aria-hidden="true"> · </span>
                              <span>{art.organizations_list}</span>
                            </div>
                          </td>
                          <td className="py-4 px-4 font-mono-tabular text-xs text-slate-700 whitespace-nowrap">
                            {art.publication_date}
                          </td>
                          <td className="py-4 px-4 text-xs text-slate-700">
                            {isRtl ? art.categories_fa : art.categories_en}
                          </td>
                          <td className="py-4 px-4 font-mono-tabular text-xs text-emerald-700 font-medium">
                            v{art.record_version} ({art.extraction_status})
                          </td>
                          <td className="py-4 px-4 sm:px-6 text-xs font-mono-tabular">
                            <a
                              href={art.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-blue-700 hover:text-blue-950 underline inline-flex items-center gap-1"
                            >
                              <span>/document/articles/{art.original_pub_id.slice(0, 8)}…</span>
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 4. PUBLICATION CATALOGUE */}
          {activeNav === 'publications' && (
            <div className="space-y-4">
              <div className="bg-white border border-teal-200 rounded-lg divide-y divide-slate-200">
                {data.publications.map((pub) => (
                  <div
                    key={pub.id}
                    className="p-4 sm:p-6 space-y-2 hover:bg-teal-50/20 transition-colors"
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="text-base font-bold text-teal-950">{pub.title}</h3>
                      <span className="text-xs font-mono-tabular text-teal-700 font-medium">
                        {pub.publication_date} · /leak/{pub.original_pub_id}
                      </span>
                    </div>
                    {pub.native_title && (
                      <div className="text-xs font-medium text-slate-600">{pub.native_title}</div>
                    )}
                    <p className="text-sm text-slate-700 leading-relaxed">{pub.description}</p>
                    <div className="pt-2 flex flex-wrap items-center justify-between gap-4 text-xs text-slate-500">
                      <div>
                        <span className="font-medium text-teal-800">
                          {isRtl ? pub.categories_fa : pub.categories_en}
                        </span>
                        <span aria-hidden="true"> · </span>
                        <span>
                          Inventory:{' '}
                          {pub.inventory
                            ?.map((i) => `${i.data_type} (${i.reported_count_label})`)
                            .join(' / ')}
                        </span>
                      </div>
                      <a
                        href={pub.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-teal-700 underline hover:text-teal-950 inline-flex items-center gap-1 font-mono-tabular break-all"
                      >
                        <span>{pub.source_url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 5. ORGANIZATIONS */}
          {activeNav === 'organizations' && (
            <div className="bg-white border border-amber-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-start border-collapse">
                  <thead>
                    <tr className="border-b border-amber-200 bg-amber-50/60 text-xs text-amber-950">
                      <th className="py-3 px-4 sm:px-6 text-start font-semibold">
                        Organization / Institution
                      </th>
                      <th className="py-3 px-4 text-start font-semibold">Native Name</th>
                      <th className="py-3 px-4 text-start font-semibold">Classification</th>
                      <th className="py-3 px-4 text-end font-semibold">Linked Articles</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {data.organizations.map((org) => (
                      <tr key={org.id} className="hover:bg-amber-50/20">
                        <td className="py-4 px-4 sm:px-6 space-y-1">
                          <div className="font-semibold text-slate-900">
                            {org.name} {org.acronym ? `(${org.acronym})` : ''}
                          </div>
                          <div className="text-xs text-slate-600">{org.description}</div>
                        </td>
                        <td className="py-4 px-4 text-xs text-slate-700">{org.native_name}</td>
                        <td className="py-4 px-4 text-xs font-mono-tabular text-amber-800 font-medium">
                          {org.org_type}
                        </td>
                        <td className="py-4 px-4 text-end font-mono-tabular text-sm font-bold text-slate-900">
                          {org.linked_articles_count}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 6. CATEGORIES */}
          {activeNav === 'categories' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.categories.map((cat) => (
                <div
                  key={cat.id}
                  className="bg-white border border-purple-200 rounded-lg p-5 sm:p-6 flex flex-col justify-between space-y-4 hover:border-purple-400 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="text-base font-bold text-purple-950">
                      {isRtl ? cat.name_fa : cat.name_en}
                    </div>
                    <div className="text-xs text-purple-700 font-medium">
                      {isRtl ? cat.name_en : cat.name_fa} · slug: {cat.slug}
                    </div>
                    <p className="text-sm text-slate-700 pt-1">{cat.description}</p>
                  </div>
                  <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-600">
                    <span className="font-mono-tabular">
                      {cat.article_count} Articles · {cat.publication_count} Catalogues
                    </span>
                    <button
                      onClick={() => {
                        setFilterCategory(cat.slug);
                        setActiveNav('search');
                      }}
                      className="font-semibold text-purple-800 hover:underline cursor-pointer"
                    >
                      {lang === 'fa' ? 'فیلتر در جستجو ←' : 'Filter in Search →'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 7. EXCEL & CSV WORKBENCH (With "Preview All Matching Records" & Cross-Dataset Audit) */}
          {activeNav === 'exports' && (
            <div className="space-y-8">
              <section className="bg-white border-2 border-emerald-300 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-emerald-900 text-white px-5 sm:px-6 py-5 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-emerald-300 tracking-wide">
                      {lang === 'fa'
                        ? 'مبدل هوشمند CSV به اکسل و پیش‌نمایش کامل رکوردها'
                        : 'CSV-TO-EXCEL SPREADSHEET READER & FULL RECORD PREVIEW'}
                    </div>
                    <h2 className="text-lg font-bold text-white">{t.csvWorkbenchTitle}</h2>
                    <p className="text-xs text-emerald-100 max-w-3xl">{t.csvWorkbenchSubtitle}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                    <label className="px-4 py-2 text-xs font-semibold text-emerald-950 bg-emerald-300 hover:bg-emerald-200 rounded-lg transition-colors inline-flex items-center gap-2 cursor-pointer">
                      <Upload className="w-4 h-4" />
                      <span>{t.csvUploadBtn}</span>
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={handleCsvFileUpload}
                        className="hidden"
                      />
                    </label>
                    {currentCsvDataset && currentCsvDataset.id > 0 && (
                      <a
                        href={`/api/csv/download/${currentCsvDataset.id}`}
                        className="px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 border border-emerald-400 rounded-lg transition-colors inline-flex items-center gap-2"
                      >
                        <FileSpreadsheet className="w-4 h-4" />
                        <span>{t.csvDownloadXlsxBtn}</span>
                      </a>
                    )}
                  </div>
                </div>

                {/* Dataset Selector, Instant Search & Admin "Preview All Matching Records" Controls */}
                <div className="p-4 sm:p-5 bg-emerald-50/60 border-b border-emerald-200 space-y-4">
                  <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-emerald-950">
                        {lang === 'fa' ? 'جدول فعال:' : 'Active CSV Table:'}
                      </span>
                      {(data.csv_datasets || []).map((ds) => (
                        <button
                          key={ds.id}
                          onClick={() =>
                            handleCsvFilterChange(ds.id, csvFilterQuery, csvPreviewAll, false)
                          }
                          className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
                            !csvCrossDatasetAudit && currentCsvDataset?.id === ds.id
                              ? 'bg-emerald-700 text-white'
                              : 'bg-white text-emerald-900 border border-emerald-300 hover:bg-emerald-100'
                          }`}
                        >
                          {ds.dataset_name} ({ds.row_count})
                        </button>
                      ))}
                      <button
                        onClick={() =>
                          handleCsvFilterChange(
                            selectedCsvId,
                            csvFilterQuery,
                            true,
                            !csvCrossDatasetAudit
                          )
                        }
                        className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer ${
                          csvCrossDatasetAudit
                            ? 'bg-indigo-700 text-white'
                            : 'bg-white text-indigo-900 border border-indigo-300 hover:bg-indigo-50'
                        }`}
                      >
                        <Layers className="w-3.5 h-3.5" />
                        <span>{t.csvCrossDatasetBtn}</span>
                      </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      <div className="relative flex-1 min-w-[220px]">
                        <input
                          type="text"
                          value={csvFilterQuery}
                          onChange={(e) =>
                            handleCsvFilterChange(
                              currentCsvDataset?.id ?? selectedCsvId,
                              e.target.value,
                              csvPreviewAll,
                              csvCrossDatasetAudit
                            )
                          }
                          placeholder={t.csvSearchPlaceholder}
                          className="w-full px-3 py-1.5 text-xs bg-white border border-emerald-300 rounded-md focus:outline-none focus:ring-2 focus:ring-emerald-600"
                        />
                      </div>

                      {/* Admin Audit Toggle: Preview All Matching Records vs Subset */}
                      <button
                        type="button"
                        onClick={() =>
                          handleCsvFilterChange(
                            currentCsvDataset?.id ?? selectedCsvId,
                            csvFilterQuery,
                            !csvPreviewAll,
                            csvCrossDatasetAudit
                          )
                        }
                        className={`px-3.5 py-1.5 text-xs font-bold rounded-md transition-colors inline-flex items-center gap-1.5 cursor-pointer ${
                          csvPreviewAll
                            ? 'bg-amber-600 text-white hover:bg-amber-700'
                            : 'bg-emerald-800 text-white hover:bg-emerald-900'
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>
                          {csvPreviewAll ? t.csvPreviewSubsetBtn : t.csvPreviewAllBtn}
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Audit Status Strip showing Displayed vs Total Matching Records */}
                  <div className="flex flex-wrap items-center justify-between gap-2 px-3.5 py-2 bg-white border border-emerald-200 rounded-md text-xs">
                    <div className="font-semibold text-slate-800">
                      {lang === 'fa' ? (
                        <span>
                          نمایش <span className="font-mono-tabular text-emerald-800">{displayedCsvCount}</span> رکورد از مجموع{' '}
                          <span className="font-mono-tabular text-emerald-800">{totalCsvMatching}</span> رکورد منطبق
                          {csvPreviewAll ? ' (حالت ممیزی کامل تمام رکوردها فعال است)' : ' (حالت پیش‌نمایش خلاصه)'}
                        </span>
                      ) : (
                        <span>
                          Showing <span className="font-mono-tabular text-emerald-800">{displayedCsvCount}</span> of{' '}
                          <span className="font-mono-tabular text-emerald-800">{totalCsvMatching}</span> matching records
                          {csvPreviewAll ? ' (Full Record Preview — All Matching Records)' : ' (Compact Subset Mode)'}
                        </span>
                      )}
                    </div>

                    {isCsvSubset && !csvPreviewAll && (
                      <button
                        type="button"
                        onClick={() =>
                          handleCsvFilterChange(
                            currentCsvDataset?.id ?? selectedCsvId,
                            csvFilterQuery,
                            true,
                            csvCrossDatasetAudit
                          )
                        }
                        className="text-xs font-bold text-indigo-700 hover:text-indigo-950 underline inline-flex items-center gap-1 cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>
                          {lang === 'fa'
                            ? `مشاهده هر ${totalCsvMatching} رکورد منطبق ←`
                            : `Preview all ${totalCsvMatching} matching records →`}
                        </span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Excel-Style Grid Table */}
                {currentCsvDataset ? (
                  <div className={`overflow-x-auto ${csvPreviewAll ? 'max-h-[640px]' : 'max-h-96'}`}>
                    <table className="w-full text-xs text-start border-collapse">
                      <thead>
                        <tr className="bg-slate-100 border-b border-slate-300 text-slate-700 sticky top-0">
                          <th className="py-2.5 px-3 border-e border-slate-300 font-mono-tabular text-center w-12 bg-slate-200">
                            #
                          </th>
                          {currentCsvDataset.headers.map((h) => (
                            <th
                              key={h}
                              className="py-2.5 px-4 border-e border-slate-200 font-bold text-slate-800 whitespace-nowrap"
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {currentCsvRows.map((r) => (
                          <tr
                            key={`${r.id}-${r.row_number}`}
                            className="hover:bg-emerald-50/60 transition-colors even:bg-slate-50/60"
                          >
                            <td className="py-2.5 px-3 border-e border-slate-200 font-mono-tabular text-center text-slate-500 bg-slate-100/70 font-semibold">
                              {r.row_number}
                            </td>
                            {currentCsvDataset.headers.map((h) => (
                              <td
                                key={h}
                                className={`py-2.5 px-4 border-e border-slate-100 text-slate-800 ${
                                  csvPreviewAll ? 'min-w-[160px]' : 'max-w-xs truncate'
                                }`}
                                title={r.cells[h] || ''}
                              >
                                {r.cells[h] || ''}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </section>

              {/* EXPORT REPORT WIZARD: Choose Specific Data Entities (Articles, Publications, Organizations, or Tags) */}
              <section className="bg-white border-2 border-indigo-300 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-slate-900 text-white px-5 sm:px-6 py-5 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'ویزارد ساخت گزارش سفارشی اکسل (.XLSX)'
                        : 'EXPORT REPORT WIZARD · CUSTOM EXCEL (.XLSX) BUILDER'}
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'انتخاب بخش‌های دلخواه برای خروجی اکسل (مقالات، انتشارات، سازمان‌ها یا برچسب‌ها)'
                        : 'Export Report Wizard — Choose Specific Data Entities to Include in Excel'}
                    </h3>
                    <p className="text-xs text-slate-300 max-w-3xl">
                      {lang === 'fa'
                        ? 'به‌جای خروجی گرفتن از تمام جداول به صورت یکجا، دقیقاً مشخص کنید کدام بخش‌ها (Articles، Publications، Organizations یا Tags) در فایل اکسل (.xlsx) شما قرار بگیرند.'
                        : 'Select exactly which data entities (Articles, Publications, Organizations, or Tags) you want to include as worksheets in your custom Excel (.xlsx) report instead of exporting everything at once.'}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() =>
                        setWizardEntities(['articles', 'publications', 'organizations', 'tags'])
                      }
                      className="px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md transition-colors cursor-pointer"
                    >
                      {lang === 'fa' ? 'انتخاب هر ۴ بخش' : 'Select All 4 Entities'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setWizardEntities(['articles'])}
                      className="px-3 py-1.5 text-xs font-semibold text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-md transition-colors cursor-pointer"
                    >
                      {lang === 'fa' ? 'فقط مقالات' : 'Articles Only'}
                    </button>
                  </div>
                </div>

                <div className="p-5 sm:p-6 space-y-5 bg-slate-50/70">
                  {/* Step 1: Select Entities Checkboxes */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      {
                        key: 'articles' as const,
                        titleEn: 'Articles',
                        titleFa: 'مقالات تحلیلی (Articles)',
                        count: data.stats.articles_count,
                        descEn: 'Titles, dates, authors, categories, summaries & source URLs',
                        descFa: 'عنوان، تاریخ انتشار، نویسنده، دسته‌بندی، خلاصه و لینک منبع',
                        borderColor: 'border-blue-500 bg-blue-50/70',
                        badgeColor: 'bg-blue-100 text-blue-900',
                      },
                      {
                        key: 'publications' as const,
                        titleEn: 'Publications',
                        titleFa: 'فهرست انتشارات (Publications)',
                        count: data.stats.publications_count,
                        descEn: 'Catalogue titles, descriptions & file inventory metadata',
                        descFa: 'عناوین فهرست انتشارات، توضیحات و متادیتای موجودی فایل‌ها',
                        borderColor: 'border-teal-500 bg-teal-50/70',
                        badgeColor: 'bg-teal-100 text-teal-900',
                      },
                      {
                        key: 'organizations' as const,
                        titleEn: 'Organizations',
                        titleFa: 'سازمان‌ها و نهادها (Organizations)',
                        count: data.stats.organizations_count,
                        descEn: 'Organization names, native names, acronyms & linked articles',
                        descFa: 'نام سازمان، نام فارسی، اختصار، نوع نهاد و تعداد مقالات مرتبط',
                        borderColor: 'border-amber-500 bg-amber-50/70',
                        badgeColor: 'bg-amber-100 text-amber-950',
                      },
                      {
                        key: 'tags' as const,
                        titleEn: 'Tags',
                        titleFa: 'برچسب‌ها و کلیدواژه‌ها (Tags)',
                        count: data.tags?.length || 10,
                        descEn: 'Tag slugs, keyword labels, linked article counts & titles',
                        descFa: 'کلیدواژه‌ها، شناسه برچسب، تعداد و عناوین مقالات مرتبط',
                        borderColor: 'border-purple-500 bg-purple-50/70',
                        badgeColor: 'bg-purple-100 text-purple-950',
                      },
                    ].map((ent) => {
                      const isSelected = wizardEntities.includes(ent.key);
                      return (
                        <label
                          key={ent.key}
                          onClick={() => toggleWizardEntity(ent.key)}
                          className={`rounded-xl p-4 border-2 transition-all cursor-pointer flex flex-col justify-between space-y-3 select-none ${
                            isSelected
                              ? `${ent.borderColor} shadow-xs`
                              : 'bg-white border-slate-200 hover:border-slate-300 opacity-80'
                          }`}
                        >
                          <div className="space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => {}}
                                className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
                              />
                              <span
                                className={`text-xs font-mono-tabular font-bold px-2 py-0.5 rounded ${ent.badgeColor}`}
                              >
                                {ent.count} {lang === 'fa' ? 'رکورد' : 'records'}
                              </span>
                            </div>
                            <div className="text-sm font-bold text-slate-900">
                              {lang === 'fa' ? ent.titleFa : ent.titleEn}
                            </div>
                            <p className="text-xs text-slate-600 leading-relaxed">
                              {lang === 'fa' ? ent.descFa : ent.descEn}
                            </p>
                          </div>
                          <div className="text-[11px] font-semibold text-indigo-800">
                            {isSelected
                              ? lang === 'fa'
                                ? '✓ در فایل اکسل قرار می‌گیرد'
                                : '✓ Included as Excel Sheet'
                              : lang === 'fa'
                              ? 'برای افزودن کلیک کنید'
                              : 'Click to include'}
                          </div>
                        </label>
                      );
                    })}
                  </div>

                  {/* Step 2: Summary & Generate Custom Excel Button */}
                  <div className="bg-white border border-indigo-200 rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="text-xs font-bold text-slate-800">
                        {lang === 'fa'
                          ? `شیت‌های انتخاب‌شده برای ساخت فایل اکسل (${wizardEntities.length} شیت):`
                          : `Selected Worksheets for Custom Excel Report (${wizardEntities.length} sheets):`}
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {wizardEntities.length > 0 ? (
                          wizardEntities.map((key) => (
                            <span
                              key={key}
                              className="px-2.5 py-0.5 text-xs font-mono-tabular font-semibold bg-indigo-100 text-indigo-900 rounded border border-indigo-300 uppercase"
                            >
                              {key}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-red-600 font-semibold">
                            {lang === 'fa'
                              ? 'لطفاً حداقل یک بخش را انتخاب کنید.'
                              : 'Please select at least one data entity above.'}
                          </span>
                        )}
                      </div>
                    </div>

                    {wizardEntities.length > 0 ? (
                      <a
                        href={`/api/export/xlsx?entities=${wizardEntities.join(',')}`}
                        className="px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-indigo-700 hover:bg-indigo-800 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                      >
                        <FileSpreadsheet className="w-4 h-4 shrink-0" />
                        <span>
                          {lang === 'fa'
                            ? `دانلود گزارش اکسل سفارشی (${wizardEntities.length} شیت انتخابی)`
                            : `Download Custom Excel Report (${wizardEntities.length} Selected Sheets)`}
                        </span>
                      </a>
                    ) : (
                      <button
                        type="button"
                        disabled
                        className="px-5 py-2.5 text-xs sm:text-sm font-bold text-slate-400 bg-slate-200 rounded-lg cursor-not-allowed"
                      >
                        {lang === 'fa' ? 'حداقل یک بخش را انتخاب کنید' : 'Select at Least 1 Entity'}
                      </button>
                    )}
                  </div>
                </div>
              </section>

              {/* Standard Archive Export Cards (.xlsx, .csv, .json) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white border border-emerald-200 border-t-4 border-t-emerald-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-emerald-950">{t.exportExcelTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportExcelDesc}</p>
                  </div>
                  <a
                    href="/api/export/xlsx"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-emerald-700 rounded-md hover:bg-emerald-800 transition-colors"
                  >
                    {t.downloadBtn} (.xlsx)
                  </a>
                </div>

                <div className="bg-white border border-sky-200 border-t-4 border-t-sky-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-sky-950">{t.exportCsvTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportCsvDesc}</p>
                  </div>
                  <a
                    href="/api/export/csv"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-sky-700 rounded-md hover:bg-sky-800 transition-colors"
                  >
                    {t.downloadBtn} (.csv)
                  </a>
                </div>

                <div className="bg-white border border-indigo-200 border-t-4 border-t-indigo-600 rounded-lg p-6 flex flex-col justify-between space-y-4">
                  <div className="space-y-2">
                    <div className="text-base font-bold text-indigo-950">{t.exportJsonTitle}</div>
                    <p className="text-xs text-slate-600 leading-relaxed">{t.exportJsonDesc}</p>
                  </div>
                  <a
                    href="/api/export/json"
                    className="w-full py-2.5 px-4 text-xs font-semibold text-center text-white bg-indigo-700 rounded-md hover:bg-indigo-800 transition-colors"
                  >
                    {t.downloadBtn} (.json)
                  </a>
                </div>
              </div>

              {/* Backup & Restore Section */}
              <div className="bg-white border border-purple-200 rounded-lg p-4 sm:p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-purple-950">{t.backupTitle}</h3>
                    <p className="text-xs text-slate-500">
                      Directory: <span className="font-mono-tabular">{data.paths.backups_dir}</span>
                    </p>
                  </div>
                  <button
                    onClick={handleCreateBackup}
                    disabled={busyAction === 'backup'}
                    className="px-4 py-2 text-xs font-semibold text-white bg-purple-700 rounded-md hover:bg-purple-800 transition-colors cursor-pointer"
                  >
                    {t.actionCreateBackup}
                  </button>
                </div>

                {confirmRestorePath && (
                  <div className="p-4 bg-amber-50 border border-amber-300 rounded-md space-y-3">
                    <div className="text-sm font-medium text-amber-950">
                      {t.confirmRestorePrompt}
                    </div>
                    <div className="text-xs font-mono-tabular text-amber-800 break-all">
                      {confirmRestorePath}
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleConfirmRestore(confirmRestorePath)}
                        className="px-3 py-1.5 text-xs font-semibold text-white bg-amber-800 rounded hover:bg-amber-900 cursor-pointer"
                      >
                        {t.confirmYes}
                      </button>
                      <button
                        onClick={() => setConfirmRestorePath(null)}
                        className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded cursor-pointer"
                      >
                        {t.confirmCancel}
                      </button>
                    </div>
                  </div>
                )}

                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2.5 px-4 text-start font-medium">Backup Filename</th>
                        <th className="py-2.5 px-4 text-start font-medium">Created UTC</th>
                        <th className="py-2.5 px-4 text-end font-medium">Size</th>
                        <th className="py-2.5 px-4 text-start font-medium">Integrity</th>
                        <th className="py-2.5 px-4 text-end font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.backups.map((b) => (
                        <tr key={b.path}>
                          <td className="py-3 px-4 font-mono-tabular text-xs">{b.filename}</td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-slate-600">
                            {b.created_at}
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-end">
                            {(b.size_bytes / 1024).toFixed(1)} KB
                          </td>
                          <td className="py-3 px-4 text-xs text-emerald-700 font-medium">
                            {b.integrity_verified ? 'PRAGMA ok' : 'Failed'}
                          </td>
                          <td className="py-3 px-4 text-end">
                            <button
                              onClick={() => setConfirmRestorePath(b.path)}
                              className="text-xs font-semibold text-purple-800 hover:underline cursor-pointer"
                            >
                              {t.restoreBtn}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 8. COLLECTION HISTORY & RECOVERY */}
          {activeNav === 'history' && (
            <div className="space-y-6">
              <div className="bg-white border border-orange-200 rounded-lg p-4 sm:p-6 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Collection Jobs & Interrupted-Task Recovery
                    </h3>
                    <p className="text-xs text-slate-500">
                      Checkpoints are persisted in collection_jobs.checkpoint_data after every page.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    {(busyAction === 'update' || busyAction === 'pipeline') && (
                      <button
                        type="button"
                        onClick={handleStopCrawl}
                        className="px-4 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-md inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                      >
                        <Square className="w-3.5 h-3.5 fill-current" />
                        <span>{lang === 'fa' ? 'توقف خزش (Stop)' : 'Stop Crawling'}</span>
                      </button>
                    )}
                    <button
                      onClick={() => handleUpdateArchive(1)}
                      disabled={busyAction !== null}
                      className="px-3.5 py-2 text-xs font-semibold text-amber-900 bg-amber-100 border border-amber-300 rounded-md hover:bg-amber-200 cursor-pointer disabled:opacity-50"
                    >
                      {t.simulateInterruptBtn}
                    </button>
                    <button
                      onClick={() => handleUpdateArchive(undefined, 12, true)}
                      disabled={busyAction !== null}
                      className="px-4 py-2 text-xs font-semibold text-white bg-sky-700 rounded-md hover:bg-sky-800 cursor-pointer disabled:opacity-50"
                    >
                      {t.actionUpdateArchive}
                    </button>
                    <button
                      onClick={() => handleUpdateArchive(undefined, 0, true)}
                      disabled={busyAction !== null}
                      className="px-4 py-2 text-xs font-bold text-indigo-950 bg-indigo-100 border border-indigo-300 rounded-md hover:bg-indigo-200 cursor-pointer disabled:opacity-50"
                    >
                      {lang === 'fa'
                        ? 'خزش عنکبوتی کامل (تمام صفحات)'
                        : 'Spider All Pages to End'}
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs text-slate-500">
                        <th className="py-2.5 px-4 text-start font-medium">Job ID</th>
                        <th className="py-2.5 px-4 text-start font-medium">Type</th>
                        <th className="py-2.5 px-4 text-start font-medium">Status</th>
                        <th className="py-2.5 px-4 text-end font-medium">Processed</th>
                        <th className="py-2.5 px-4 text-start font-medium">Started UTC</th>
                        <th className="py-2.5 px-4 text-end font-medium">Recovery</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.jobs.map((job) => (
                        <tr key={job.id}>
                          <td className="py-3 px-4 font-mono-tabular text-xs">#{job.id}</td>
                          <td className="py-3 px-4 font-mono-tabular text-xs">{job.job_type}</td>
                          <td className="py-3 px-4 text-xs font-semibold">
                            <span
                              className={
                                job.status === 'COMPLETED'
                                  ? 'text-emerald-700'
                                  : job.status === 'INTERRUPTED'
                                  ? 'text-amber-700'
                                  : 'text-slate-700'
                              }
                            >
                              {job.status}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-end">
                            {job.processed_count} / {job.total_discovered}
                          </td>
                          <td className="py-3 px-4 font-mono-tabular text-xs text-slate-500">
                            {job.started_at}
                          </td>
                          <td className="py-3 px-4 text-end">
                            {job.status === 'INTERRUPTED' && (
                              <button
                                onClick={() => handleResumeJob(job.id)}
                                className="px-3 py-1 text-xs font-semibold text-white bg-amber-700 rounded hover:bg-amber-800 cursor-pointer"
                              >
                                {t.resumeJobBtn}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Granular Per-URL Audit History */}
              <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                <div className="px-4 sm:px-6 py-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-700">
                  Per-URL Collection Audit Log (collection_history)
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-start border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        <th className="py-2.5 px-4 sm:px-6 text-start font-medium">Target URL</th>
                        <th className="py-2.5 px-4 text-start font-medium">Type</th>
                        <th className="py-2.5 px-4 text-start font-medium">Action</th>
                        <th className="py-2.5 px-4 sm:px-6 text-start font-medium">Audit Note</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {data.history.slice(0, 20).map((h) => (
                        <tr key={h.id}>
                          <td className="py-2.5 px-4 sm:px-6 font-mono-tabular text-slate-800 break-all">
                            {h.target_url}
                          </td>
                          <td className="py-2.5 px-4 font-mono-tabular">{h.record_type}</td>
                          <td
                            className={`py-2.5 px-4 font-mono-tabular font-semibold ${
                              h.action_taken === 'EXCLUDED_POLICY'
                                ? 'text-amber-700'
                                : 'text-emerald-700'
                            }`}
                          >
                            {h.action_taken}
                          </td>
                          <td className="py-2.5 px-4 sm:px-6 text-slate-600">{h.message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 9. SETTINGS, WINDOWS INSTALLER (.EXE), STORAGE PATH & SCHEDULED COLLECTION PANEL */}
          {activeNav === 'settings' && (
            <div className="space-y-6">
              {/* WINDOWS INSTALLER (.EXE) & USER-CONFIGURABLE STORAGE PATH */}
              <section className="bg-white border-2 border-indigo-300 rounded-xl overflow-hidden shadow-xs">
                <div className="bg-slate-900 text-white px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800">
                  <div className="space-y-1">
                    <div className="text-xs font-bold text-sky-400 uppercase tracking-wider">
                      {lang === 'fa'
                        ? 'نصب‌کننده هوشمند ویندوز (.EXE) به همراه بررسی و نصب خودکار پایتون و پیش‌نیازها'
                        : 'STEP-BY-STEP WINDOWS INSTALLER (.EXE) WITH AUTOMATIC PYTHON & PREREQUISITE SETUP'}
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-white">
                      {lang === 'fa'
                        ? 'دانلود فایل نصب ویندوز (WikIranArchive_Setup.exe) — نصب گام‌به‌گام پیش‌نیازها و برنامه'
                        : 'WikIran Archive Windows Setup (WikIranArchive_Setup.exe) & Data Storage Directory'}
                    </h3>
                    <p className="text-xs text-slate-300 max-w-3xl">
                      {lang === 'fa'
                        ? 'فایل WikIranArchive_Setup.exe ابتدا سیستم را بررسی می‌کند؛ اگر پایتون ۳.۱۱ یا پیش‌نیازها نصب نباشند، به‌طور خودکار آن‌ها را دانلود و نصب می‌کند و سپس برنامه، دیتابیس SQLite و میانبر دسکتاپ را در مسیر دلخواه شما نصب می‌نماید.'
                        : 'WikIranArchive_Setup.exe checks your PC first: if Python 3.11 or any required component is missing, the installer automatically downloads and installs them step-by-step, then installs WikIran Archive, the SQLite database, and the Desktop shortcut.'}
                    </p>
                  </div>
                  <a
                    href="/api/download/windows-installer-exe"
                    className="px-5 py-2.5 text-xs sm:text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs shrink-0"
                  >
                    <HardDriveDownload className="w-4 h-4 shrink-0" />
                    <span>
                      {lang === 'fa'
                        ? 'دانلود نصب‌کننده ویندوز (WikIranArchive_Setup.exe)'
                        : 'Download Windows Installer (WikIranArchive_Setup.exe)'}
                    </span>
                  </a>
                </div>

                <div className="p-5 sm:p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 bg-slate-50/60">
                  {/* Left Column: User-Selectable Storage Path */}
                  <form
                    onSubmit={handleSaveStoragePath}
                    className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-indigo-100 text-indigo-950">
                          {lang === 'fa' ? 'مسیر ذخیره‌سازی اطلاعات' : 'CUSTOM STORAGE PATH'}
                        </span>
                        <span className="text-xs font-mono-tabular text-emerald-700 font-semibold">
                          SQLite DB + Excel + Backups
                        </span>
                      </div>
                      <h4 className="text-sm sm:text-base font-bold text-slate-900">
                        {lang === 'fa'
                          ? 'انتخاب محل ذخیره دیتابیس، فایل‌های اکسل و نسخه‌های پشتیبان'
                          : 'Choose Where to Store Archive Data, Excel Reports & Backups'}
                      </h4>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        {lang === 'fa'
                          ? 'مسیر دلخواه خود را روی ویندوز وارد یا انتخاب کنید. هم در زمان نصب فایل .exe و هم در اینجا می‌توانید مشخص کنید تمام اطلاعات در کدام پوشه یا درایو ذخیره شوند.'
                          : 'Specify the folder on your computer where all downloaded articles, publications, SQLite database files, Excel exports, and backups should be stored. You can also choose this folder inside the .exe installer wizard.'}
                      </p>

                      <div className="space-y-2 pt-1">
                        <label className="block text-xs font-semibold text-slate-700">
                          {lang === 'fa' ? 'مسیر پوشه ذخیره‌سازی (Storage Path):' : 'Storage Folder Path:'}
                        </label>
                        <div className="flex flex-col sm:flex-row gap-2">
                          <input
                            type="text"
                            dir="ltr"
                            value={storagePathInput}
                            onChange={(e) => setStoragePathInput(e.target.value)}
                            placeholder="C:\WikIranArchive"
                            className="flex-1 px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
                          />
                          <button
                            type="submit"
                            disabled={busyAction === 'save-storage-path'}
                            className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md transition-colors cursor-pointer whitespace-nowrap"
                          >
                            {lang === 'fa' ? 'ذخیره مسیر' : 'Save Storage Path'}
                          </button>
                        </div>

                        {/* Quick Path Presets */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[11px] text-slate-500">
                            {lang === 'fa' ? 'مسیرهای پیشنهادی:' : 'Presets:'}
                          </span>
                          {[
                            'C:\\WikIranArchive',
                            'D:\\WikIranArchive',
                            'C:\\Users\\Public\\WikIranArchive',
                          ].map((preset) => (
                            <button
                              key={preset}
                              type="button"
                              onClick={() => setStoragePathInput(preset)}
                              className="px-2 py-0.5 text-[11px] font-mono-tabular bg-slate-100 hover:bg-indigo-50 text-slate-700 hover:text-indigo-800 border border-slate-300 rounded cursor-pointer"
                            >
                              {preset}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-slate-100 space-y-1 text-xs text-slate-600 font-mono-tabular" dir="ltr">
                      <div>Active Base Folder: {data.paths.base_dir}</div>
                      <div>SQLite Database: {data.paths.db_path}</div>
                      <div>Excel Exports: {data.paths.exports_dir}</div>
                    </div>
                  </form>

                  {/* Right Column: One-File Windows Installer (.exe) Step-by-Step Prerequisite & App Installer */}
                  <div className="bg-white border border-emerald-200 rounded-xl p-5 flex flex-col justify-between space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded bg-emerald-100 text-emerald-950">
                          {lang === 'fa'
                            ? 'نصب خودکار پایتون، کتابخانه‌ها و برنامه'
                            : 'ALL-IN-ONE PREREQUISITE + APP INSTALLER (.EXE)'}
                        </span>
                        <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                      </div>
                      <h4 className="text-sm sm:text-base font-bold text-slate-900">
                        {lang === 'fa'
                          ? 'مراحل خودکار داخل WikIranArchive_Setup.exe (بدون نیاز به هیچ دستور دستی)'
                          : 'What WikIranArchive_Setup.exe Does Step-by-Step Automatically'}
                      </h4>
                      <ol className="list-decimal list-inside space-y-1.5 text-xs text-slate-700 leading-relaxed">
                        <li>
                          {lang === 'fa'
                            ? 'گام ۱ (بررسی سیستم): نصب‌کننده ابتدا کامپیوتر ویندوزی را بررسی می‌کند که آیا Python 3.11+، کتابخانه‌های مورد نیاز و WebView2 نصب هستند یا خیر.'
                            : 'Step 1 (System Check): Inspects the PC to check if Python 3.11+, required packages, and Edge WebView2 Runtime are installed.'}
                        </li>
                        <li>
                          {lang === 'fa'
                            ? 'گام ۲ (نصب خودکار پیش‌نیازها): اگر پایتون یا کتابخانه‌ای روی سیستم نباشد، نصب‌کننده به‌طور خودکار فایل نصبی رسمی Python 3.11 (64-bit) و پکیج‌ها (requirements.txt) را دانلود و بی‌صدا نصب می‌کند.'
                            : 'Step 2 (Auto-Install Python & Packages): If Python or packages are missing, the installer automatically downloads and silently installs Python 3.11.9 (64-bit) and runs pip install -r requirements.txt.'}
                        </li>
                        <li>
                          {lang === 'fa'
                            ? 'گام ۳ (نصب برنامه و دیتابیس): فایل اجرایی WikIranArchive.exe، موتور کامل پایتون، دیتابیس SQLite و گزارش‌های اکسل را در مسیر ذخیره‌سازی انتخابی شما نصب کرده و میانبر دسکتاپ را می‌سازد.'
                            : 'Step 3 (Install App & Database): Installs WikIranArchive.exe, the full Python package, SQLite FTS5 database, and Excel exports into your chosen Storage Path and creates the Desktop shortcut.'}
                        </li>
                        <li>
                          {lang === 'fa'
                            ? 'گام ۴ (اجرای برنامه): برنامه WikIran Archive به‌طور خودکار باز می‌شود.'
                            : 'Step 4 (Launch): Automatically launches WikIran Archive ready for use.'}
                        </li>
                      </ol>
                    </div>

                    <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                      <a
                        href="/api/download/windows-installer-exe"
                        className="flex-1 py-2.5 px-4 text-xs sm:text-sm font-bold text-center text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors inline-flex items-center justify-center gap-2 shadow-xs"
                      >
                        <HardDriveDownload className="w-4 h-4 shrink-0" />
                        <span>
                          {lang === 'fa'
                            ? 'دانلود WikIranArchive_Setup.exe'
                            : 'Download WikIranArchive_Setup.exe'}
                        </span>
                      </a>
                      <a
                        href="/api/download/windows-package"
                        className="py-2.5 px-3.5 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg transition-colors inline-flex items-center gap-1.5"
                      >
                        <span>
                          {lang === 'fa'
                            ? 'اسکریپت‌های Inno Setup (.iss) و ZIP'
                            : 'Inno Setup (.iss) & Build Kit (.zip)'}
                        </span>
                      </a>
                    </div>
                  </div>
                </div>
              </section>

              {/* SCHEDULED COLLECTION PANEL */}
              <form
                onSubmit={handleSaveSchedule}
                className="bg-white border-2 border-cyan-300 rounded-xl overflow-hidden shadow-xs"
              >
                <div className="bg-cyan-950 text-white px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold text-cyan-300">
                      BACKGROUND TASK RUNNER · INCREMENTAL ARCHIVE SERVICE
                    </div>
                    <h3 className="text-base font-bold text-white">{t.schedulerTitle}</h3>
                    <p className="text-xs text-cyan-100">{t.schedulerSubtitle}</p>
                  </div>
                  <div className="text-xs font-mono-tabular bg-cyan-900 px-3 py-1.5 rounded border border-cyan-700">
                    Status: {data.schedule?.runner_status} · Next: {data.schedule?.next_run_at}
                  </div>
                </div>

                <div className="p-4 sm:p-6 space-y-5">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleEnabledLabel}
                      </label>
                      <select
                        value={schedEnabled ? 'true' : 'false'}
                        onChange={(e) => setSchedEnabled(e.target.value === 'true')}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-semibold"
                      >
                        <option value="true">Enabled (Active Background Runner)</option>
                        <option value="false">Paused (Manual Updates Only)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleFrequencyLabel}
                      </label>
                      <select
                        value={schedFreq}
                        onChange={(e) => setSchedFreq(e.target.value)}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white"
                      >
                        <option value="daily">Daily (Every Day at Specified Time)</option>
                        <option value="weekly">Weekly (Selected Day of Week)</option>
                        <option value="every_6h">Every 6 Hours</option>
                        <option value="every_12h">Every 12 Hours</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleTimeLabel}
                      </label>
                      <input
                        type="time"
                        value={schedTime}
                        onChange={(e) => setSchedTime(e.target.value)}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleDayLabel}
                      </label>
                      <select
                        value={schedDay}
                        onChange={(e) => setSchedDay(e.target.value)}
                        disabled={schedFreq !== 'weekly'}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white disabled:opacity-50"
                      >
                        <option value="sunday">Sunday</option>
                        <option value="monday">Monday</option>
                        <option value="tuesday">Tuesday</option>
                        <option value="wednesday">Wednesday</option>
                        <option value="thursday">Thursday</option>
                        <option value="friday">Friday</option>
                        <option value="saturday">Saturday</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-slate-700">
                        {t.scheduleMaxItemsLabel}
                      </label>
                      <input
                        type="number"
                        min={1}
                        max={25}
                        value={schedMaxItems}
                        onChange={(e) => setSchedMaxItems(Number(e.target.value))}
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-md bg-white font-mono-tabular"
                      />
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4">
                    <div className="text-xs text-slate-500 font-mono-tabular">
                      Last Background Run: {data.schedule?.last_run_at} · Next Scheduled Run:{' '}
                      <span className="font-semibold text-cyan-900">
                        {data.schedule?.next_run_at}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={handleTriggerScheduledRunNow}
                        disabled={busyAction === 'schedule-run'}
                        className="px-4 py-2 text-xs font-semibold text-cyan-950 bg-cyan-100 border border-cyan-300 rounded-md hover:bg-cyan-200 transition-colors cursor-pointer"
                      >
                        {t.scheduleRunNowBtn}
                      </button>
                      <button
                        type="submit"
                        disabled={busyAction === 'schedule-save'}
                        className="px-4 py-2 text-xs font-semibold text-white bg-cyan-800 rounded-md hover:bg-cyan-900 transition-colors cursor-pointer"
                      >
                        {t.scheduleSaveBtn}
                      </button>
                    </div>
                  </div>
                </div>
              </form>

              {/* Archive Scope & Language Preferences */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-4">
                <h3 className="text-base font-bold text-slate-900">
                  {lang === 'fa'
                    ? 'تنظیمات دامنه استخراج، زبان و مسیر ذخیره‌سازی داده'
                    : 'Extraction Scope, Language & External AppData Storage'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div className="p-4 border border-indigo-200 bg-indigo-50/40 rounded-md space-y-2">
                    <div className="text-xs font-bold text-indigo-950">
                      {lang === 'fa'
                        ? 'دامنه آرشیو و جستجو (ایمیل‌ها، فایل‌ها و اسناد بانکی)'
                        : 'Archive & Search Scope (Emails, Files & Banking)'}
                    </div>
                    <p className="text-xs text-slate-600">
                      {isFullUnredactedMode
                        ? lang === 'fa'
                          ? 'فعال: تمام ایمیل‌ها (/document/emails/*)، فایل‌ها و اسناد بانکی بدون حذفیات در دسترس هستند.'
                          : 'Active: All emails (/document/emails/*), raw files, and banking records are unlocked.'
                        : lang === 'fa'
                        ? 'فیلترشده: مکاتبات و اسناد بانکی مخفی هستند.'
                        : 'Filtered: Private correspondence and banking identifiers are filtered.'}
                    </p>
                    <button
                      onClick={() => handleToggleArchiveScope(!isFullUnredactedMode)}
                      className="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded cursor-pointer"
                    >
                      {isFullUnredactedMode ? t.switchToFilteredModeBtn : t.switchToFullModeBtn}
                    </button>
                  </div>

                  <div className="p-4 border border-slate-200 rounded-md space-y-2">
                    <div className="text-xs text-slate-500">Default Interface Language</div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleLanguageSwitch('en')}
                        className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                          lang === 'en'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        English (LTR)
                      </button>
                      <button
                        onClick={() => handleLanguageSwitch('fa')}
                        className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                          lang === 'fa'
                            ? 'bg-indigo-600 text-white'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        فارسی (RTL)
                      </button>
                    </div>
                  </div>

                  <div className="p-4 border border-slate-200 rounded-md space-y-1">
                    <div className="text-xs text-slate-500">External AppData Storage Path</div>
                    <div className="font-mono-tabular text-xs break-all text-slate-800">
                      {data.paths.db_path}
                    </div>
                  </div>
                </div>
              </div>

              {/* System Diagnostics, Reconnaissance & Source Code Inspector */}
              <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      System Diagnostics, Reconnaissance & Packaging Inspector
                    </h3>
                    <p className="text-xs text-slate-500">
                      Verify live reconnaissance, SQLite schema, Inno Setup script (installer/wikiran_archive_setup.iss), and automated unit tests.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      onClick={handleRunRecon}
                      disabled={busyAction === 'recon'}
                      className="px-3.5 py-2 text-xs font-semibold text-slate-900 bg-slate-100 border border-slate-300 rounded-md hover:bg-slate-200 inline-flex items-center gap-1.5 cursor-pointer"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{t.runReconBtn}</span>
                    </button>
                    <button
                      onClick={handleRunTests}
                      disabled={busyAction === 'tests'}
                      className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-800 rounded-md hover:bg-emerald-900 inline-flex items-center gap-1.5 cursor-pointer"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>{t.runTestsBtn}</span>
                    </button>
                  </div>
                </div>

                {testOutput && (
                  <div className="bg-slate-950 text-emerald-400 p-4 rounded-md font-mono-tabular text-xs overflow-x-auto whitespace-pre">
                    {testOutput}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  {[
                    { key: 'reconnaissance', label: 'RECONNAISSANCE_REPORT.md' },
                    { key: 'schema', label: 'DATABASE_SCHEMA.md (15 Tables)' },
                    { key: 'architecture', label: 'ARCHITECTURE.md' },
                    { key: 'status', label: 'PROJECT_STATUS.md' },
                    { key: 'pyside_ui', label: 'ui/main_window.py (PySide6)' },
                    { key: 'migrations_py', label: 'database/migrations.py' },
                    { key: 'recon_py', label: 'collector/reconnaissance.py' },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => loadDoc(tab.key)}
                      className={`px-3 py-1.5 text-xs font-mono-tabular rounded border transition-colors cursor-pointer ${
                        docKey === tab.key
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      <FileCode2 className="w-3 h-3 inline me-1" />
                      {tab.label}
                    </button>
                  ))}
                </div>

                {docContent && (
                  <div className="border border-slate-200 rounded-md overflow-hidden">
                    <div className="bg-slate-100 px-4 py-2 text-xs font-mono-tabular font-semibold text-slate-700 border-b border-slate-200">
                      {docContent.filename}
                    </div>
                    <pre className="p-4 bg-slate-50 text-xs font-mono-tabular text-slate-800 overflow-x-auto whitespace-pre-wrap max-h-96">
                      {docContent.content}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 10. HELP / OPERATOR MANUAL */}
          {activeNav === 'help' && (
            <div className="bg-white border border-slate-200 rounded-lg p-4 sm:p-6 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-4">
                <h2 className="text-lg font-bold text-slate-900">
                  {lang === 'fa'
                    ? 'راهنمای کاربری برنامه (فارسی / انگلیسی)'
                    : 'User Guide & Reference Manual (English / Persian)'}
                </h2>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => setShowWorkflowModal(true)}
                    className="px-3 py-1.5 text-xs font-bold rounded bg-amber-400 text-slate-950 hover:bg-amber-300 cursor-pointer"
                  >
                    {t.howToWorkBtn}
                  </button>
                  <button
                    onClick={() => loadDoc('manual_en')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                      docKey === 'manual_en'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    OPERATOR_MANUAL_EN.md
                  </button>
                  <button
                    onClick={() => loadDoc('manual_fa')}
                    className={`px-3 py-1.5 text-xs font-semibold rounded cursor-pointer ${
                      docKey === 'manual_fa'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    OPERATOR_MANUAL_FA.md
                  </button>
                </div>
              </div>
              {docContent && (
                <pre className="text-sm text-slate-800 whitespace-pre-wrap leading-relaxed font-sans">
                  {docContent.content}
                </pre>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
