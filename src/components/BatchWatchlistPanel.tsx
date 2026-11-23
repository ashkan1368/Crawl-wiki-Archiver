import React, { useState } from 'react';
import {
  FileSpreadsheet,
  Upload,
  Download,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Search,
  ExternalLink,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Info,
  ClipboardList,
  Globe,
} from 'lucide-react';
import { Language } from '../i18n';

interface EvidenceHit {
  source_bucket: string;
  record_type: string;
  title: string;
  programs_or_leak: string;
  publication_date: string;
  snippet: string;
  source_url: string;
}

interface ScreenedRow {
  row_number: number;
  name: string;
  alias: string;
  entity_type: string;
  country: string;
  reference_id: string;
  notes: string;
  risk_level: 'HIGH_RISK' | 'ELEVATED_RISK' | 'CLEAR';
  risk_label: string;
  total_hits: number;
  ofac_hits: number;
  opensanctions_hits: number;
  wikiran_offline_hits: number;
  wikiran_live_hits: number;
  wikiran_live_total_int: number;
  wikiran_live_total_label: string;
  top_match_title: string;
  top_match_source: string;
  top_match_url: string;
  sanctions_or_leak_tags: string;
  evidence_hits: EvidenceHit[];
}

interface BatchScreenResponse {
  ok: boolean;
  error?: string;
  summary?: {
    screened_at: string;
    total_screened: number;
    high_risk_count: number;
    elevated_risk_count: number;
    clear_count: number;
    live_wikiran_enabled: boolean;
    live_queries_used: number;
    live_capped: boolean;
    newly_cached_wikiran_docs: number;
    detected_format: string;
    detected_columns: string[];
    skipped_rows: number;
  };
  results?: ScreenedRow[];
  reports?: {
    csv_path: string;
    csv_filename: string;
    xlsx_path: string;
    xlsx_filename: string;
  };
}

interface BatchWatchlistPanelProps {
  lang: Language;
  onDataUpdated: () => void;
}

const SAMPLE_PASTE_TEXT = `Name,Entity_Type,Alias_or_Alt_Name,Country,Reference_ID,Notes
Bank Sepah,Bank,بانک سپه,Iran,TRD-2026-001,Banking counterparty check
Sahara Thunder,Company,صحرا تاندر,Iran,TRD-2026-002,Shipping & front company check
Sepehr Energy Jahan,Company,سپهر انرژی جهان,Iran,TRD-2026-003,Energy sector check
Nordic Clean Logistics GmbH,Company,,Germany,TRD-2026-004,Routine European supplier check`;

export const BatchWatchlistPanel: React.FC<BatchWatchlistPanelProps> = ({
  lang,
  onDataUpdated,
}) => {
  const isFa = lang === 'fa';
  const [pasteText, setPasteText] = useState<string>('');
  const [uploadedFileName, setUploadedFileName] = useState<string>('');
  const [uploadedFileB64, setUploadedFileB64] = useState<string>('');
  const [includeLiveWikiran, setIncludeLiveWikiran] = useState<boolean>(true);
  const [isScreening, setIsScreening] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [response, setResponse] = useState<BatchScreenResponse | null>(null);
  const [riskFilter, setRiskFilter] = useState<'ALL' | 'HIGH_RISK' | 'ELEVATED_RISK' | 'CLEAR'>('ALL');
  const [tableSearch, setTableSearch] = useState<string>('');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [showFormatGuide, setShowFormatGuide] = useState<boolean>(true);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErrorMsg('');
    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === 'string') {
        const idx = result.indexOf(',');
        const b64 = idx >= 0 ? result.slice(idx + 1) : result;
        setUploadedFileB64(b64);
      }
    };
    reader.readAsDataURL(file);
  };

  const clearUpload = () => {
    setUploadedFileName('');
    setUploadedFileB64('');
  };

  const handleRunScreening = async () => {
    if (!uploadedFileB64 && !pasteText.trim()) {
      setErrorMsg(
        isFa
          ? 'لطفاً ابتدا یک فایل Excel/CSV انتخاب کنید یا نام شرکت‌ها/اشخاص را در کادر زیر وارد نمایید.'
          : 'Please upload an Excel/CSV file or paste at least one entity name below.'
      );
      return;
    }

    setIsScreening(true);
    setErrorMsg('');
    setExpandedRow(null);
    try {
      const res = await fetch('/api/watchlist/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_b64: uploadedFileB64 || undefined,
          filename: uploadedFileName || '',
          raw_text: uploadedFileB64 ? undefined : pasteText,
          include_live_wikiran: includeLiveWikiran,
          max_live_queries: 80,
        }),
      });
      const json: BatchScreenResponse = await res.json();
      if (!json.ok) {
        setErrorMsg(json.error || 'Batch screening failed.');
      } else {
        setResponse(json);
        onDataUpdated();
      }
    } catch (err) {
      setErrorMsg(String(err));
    } finally {
      setIsScreening(false);
    }
  };

  const filteredResults = (response?.results || []).filter((row) => {
    if (riskFilter !== 'ALL' && row.risk_level !== riskFilter) return false;
    if (tableSearch.trim()) {
      const q = tableSearch.trim().toLowerCase();
      const hay = `${row.name} ${row.alias} ${row.reference_id} ${row.country} ${row.top_match_title} ${row.sanctions_or_leak_tags}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <section className="bg-slate-900 text-white rounded-xl border border-slate-800 p-5 sm:p-6 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-1.5 max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-400">
              {isFa
                ? 'غربالگری گروهی طرف‌های معامله (OFAC + OpenSanctions + WikIran 3.1M)'
                : 'BATCH COUNTERPARTY COMPLIANCE SCREENER (OFAC + OPENSANCTIONS + WIKIRAN 3.1M)'}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-white">
              {isFa
                ? 'بررسی هم‌زمان ده‌ها یا هزاران شرکت، شخص، بانک و کشتی با فایل Excel یا CSV'
                : 'Screen an Excel / CSV Watchlist Across All Sanctions & WikIran Archives'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {isFa
                ? 'فایل نمونه استاندارد را دانلود کنید، نام‌های مورد نظر همکاران خود را در آن وارد نمایید و آپلود کنید. برنامه هر نام را در OFAC، OpenSanctions، شرکت‌های پوششی و کشتی‌های ویکی‌ایران و آرشیو ۳.۱ میلیونی اسناد بررسی کرده و گزارش ریسک اکسل رنگی تحویل می‌دهد.'
                : 'Download the exact template below for your colleagues, fill in counterparty names, and upload. Every row is screened against OFAC, OpenSanctions, WikIran Front Companies/Vessels, and optionally live WikIran 3.1M leak documents (auto-saving every hit offline), producing a color-coded Excel Risk Report.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <a
              href="/api/watchlist/template/xlsx"
              className="px-4 py-2.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
            >
              <FileSpreadsheet className="w-4 h-4 shrink-0" />
              <span>{isFa ? 'دانلود قالب اکسل (.xlsx)' : 'Download Excel Template (.xlsx)'}</span>
            </a>
            <a
              href="/api/watchlist/template/csv"
              className="px-4 py-2.5 text-xs font-bold text-slate-100 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors inline-flex items-center gap-2"
            >
              <Download className="w-4 h-4 shrink-0" />
              <span>{isFa ? 'دانلود قالب CSV (.csv)' : 'Download CSV Template (.csv)'}</span>
            </a>
          </div>
        </div>
      </section>

      {/* Exact Format Reference Guide for Colleagues */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
        <button
          type="button"
          onClick={() => setShowFormatGuide((v) => !v)}
          className="w-full px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3 text-left cursor-pointer hover:bg-slate-100/70 transition-colors"
        >
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="text-sm font-bold text-slate-900">
              {isFa
                ? 'فرمت دقیق فایل ورودی برای همکاران (ستون‌های استاندارد Excel / CSV)'
                : 'Exact Input File Format Guide for Colleagues (Standard Excel / CSV Columns)'}
            </span>
          </div>
          {showFormatGuide ? (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-500" />
          )}
        </button>

        {showFormatGuide && (
          <div className="p-5 space-y-4">
            <div className="overflow-x-auto border border-slate-200 rounded-lg">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-slate-900 text-white">
                  <tr>
                    <th className="px-3.5 py-2.5 font-bold">
                      {isFa ? 'نام ستون (ردیف ۱)' : 'Column Header (Row 1)'}
                    </th>
                    <th className="px-3.5 py-2.5 font-bold">
                      {isFa ? 'وضعیت' : 'Required?'}
                    </th>
                    <th className="px-3.5 py-2.5 font-bold">
                      {isFa ? 'نحوه صحیح تکمیل توسط همکاران' : 'How Colleagues Should Fill It'}
                    </th>
                    <th className="px-3.5 py-2.5 font-bold">
                      {isFa ? 'مثال صحیح' : 'Good Example'}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  <tr>
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-indigo-900">Name</td>
                    <td className="px-3.5 py-2">
                      <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-900 font-bold text-[11px]">
                        {isFa ? 'الزامی' : 'REQUIRED'}
                      </span>
                    </td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa
                        ? 'فقط یک نام شرکت، شخص، بانک، صرافی یا کشتی در هر ردیف (انگلیسی یا فارسی). دو شرکت را در یک سلول ننویسید.'
                        : 'Put ONE company, person, bank, exchange house, or vessel name per row (English or Persian). Do not mix two companies in one cell.'}
                    </td>
                    <td className="px-3.5 py-2 font-mono-tabular text-slate-800">Sahara Thunder</td>
                  </tr>
                  <tr className="bg-slate-50/50">
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-slate-800">Entity_Type</td>
                    <td className="px-3.5 py-2 text-slate-500">{isFa ? 'اختیاری' : 'Optional'}</td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa
                        ? 'نوع نهاد: Company, Person, Vessel, Bank, Exchange (یا خالی بگذارید).'
                        : 'Use Company, Person, Vessel, Bank, or Exchange — or leave blank.'}
                    </td>
                    <td className="px-3.5 py-2 font-mono-tabular text-slate-800">Company</td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-slate-800">Alias_or_Alt_Name</td>
                    <td className="px-3.5 py-2 text-slate-500">{isFa ? 'اختیاری (جستجو می‌شود)' : 'Optional (Also Screened)'}</td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa
                        ? 'معادل فارسی/انگلیسی، نام دوم یا شماره IMO کشتی. این ستون هم به‌طور خودکار بررسی می‌شود! چند نام را با ; جدا کنید.'
                        : 'Persian/English equivalent, alternate spelling, or vessel IMO number. Automatically screened too! Separate multiple aliases with ";".'}
                    </td>
                    <td className="px-3.5 py-2 font-mono-tabular text-slate-800">صحرا تاندر; IMO 9234567</td>
                  </tr>
                  <tr className="bg-slate-50/50">
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-slate-800">Country</td>
                    <td className="px-3.5 py-2 text-slate-500">{isFa ? 'اختیاری' : 'Optional'}</td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa ? 'کشور طرف معامله یا پرچم کشتی برای گزارش نهایی.' : 'Counterparty country or vessel flag for your report.'}
                    </td>
                    <td className="px-3.5 py-2 font-mono-tabular text-slate-800">UAE / Iran</td>
                  </tr>
                  <tr>
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-slate-800">Reference_ID</td>
                    <td className="px-3.5 py-2 text-slate-500">{isFa ? 'اختیاری' : 'Optional'}</td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa
                        ? 'کد داخلی فاکتور، قرارداد یا مشتری تا نتیجه ریسک را راحت با پرونده خود تطبیق دهید.'
                        : 'Your internal client, invoice, or contract code to trace results back to your trade file.'}
                    </td>
                    <td className="px-3.5 py-2 font-mono-tabular text-slate-800">TRD-2026-042</td>
                  </tr>
                  <tr className="bg-slate-50/50">
                    <td className="px-3.5 py-2 font-mono-tabular font-bold text-slate-800">Notes</td>
                    <td className="px-3.5 py-2 text-slate-500">{isFa ? 'اختیاری' : 'Optional'}</td>
                    <td className="px-3.5 py-2 text-slate-700">
                      {isFa ? 'یادداشت داخلی (مستقیماً در گزارش ریسک اکسل کپی می‌شود).' : 'Internal trade notes (carried directly into the output Risk Report Excel).'}
                    </td>
                    <td className="px-3.5 py-2 text-slate-700">Q4 Petrochemical Buyer</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="bg-indigo-50/70 border border-indigo-200 rounded-lg px-4 py-2.5 text-xs text-indigo-950 flex flex-wrap items-center justify-between gap-2">
              <span>
                {isFa
                  ? 'نکته: برنامه هوشمند است — اگر همکاران فایل Excel با ستون‌های «Company»، «Counterparty»، «نام» یا حتی فقط یک لیست ساده (در هر خط یک نام) بفرستند، به‌طور خودکار تشخیص داده و پردازش می‌کند.'
                  : 'Tip: The parser is forgiving — if colleagues send an Excel/CSV with headers like "Company", "Counterparty", "Vessel", or even a plain 1-name-per-line list, it still reads it accurately.'}
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Input Section: File Upload OR Quick Paste */}
      <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Option A: Upload File */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-5 bg-slate-50/60 flex flex-col justify-between space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <Upload className="w-4 h-4 text-indigo-600" />
                <span>{isFa ? 'روش ۱: آپلود فایل Excel (.xlsx) یا CSV' : 'Option 1: Upload Excel (.xlsx) or CSV File'}</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                {isFa
                  ? 'فایل تکمیل‌شده قالب (تا ۵٬۰۰۰ ردیف) را انتخاب کنید. فایل‌های .xlsx، .csv و .txt پشتیبانی می‌شوند.'
                  : 'Select your filled Excel or CSV watchlist (up to 5,000 rows). Supports .xlsx, .csv, .tsv, and .txt.'}
              </p>
            </div>

            <div className="space-y-3">
              <label className="block w-full cursor-pointer">
                <span className="sr-only">Choose watchlist file</span>
                <input
                  type="file"
                  accept=".xlsx,.xlsm,.csv,.tsv,.txt"
                  onChange={handleFileChange}
                  className="block w-full text-xs text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 cursor-pointer"
                />
              </label>

              {uploadedFileName && (
                <div className="flex items-center justify-between gap-2 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2 text-xs text-emerald-900">
                  <span className="font-mono-tabular font-semibold truncate">
                    {isFa ? 'فایل آماده بررسی:' : 'File ready:'} {uploadedFileName}
                  </span>
                  <button
                    type="button"
                    onClick={clearUpload}
                    className="text-rose-700 hover:underline font-bold shrink-0 cursor-pointer"
                  >
                    {isFa ? 'حذف' : 'Remove'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Option B: Paste Directly */}
          <div className="border border-slate-200 rounded-xl p-5 bg-white flex flex-col justify-between space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
                <ClipboardList className="w-4 h-4 text-emerald-600" />
                <span>{isFa ? 'روش ۲: چسباندن مستقیم نام‌ها (در هر خط یک نام)' : 'Option 2: Quick Paste Names (One Per Line or CSV)'}</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  clearUpload();
                  setPasteText(SAMPLE_PASTE_TEXT);
                }}
                className="text-xs font-semibold text-indigo-700 hover:text-indigo-900 underline cursor-pointer"
              >
                {isFa ? 'درج ۴ نمونه آزمایشی' : 'Load 4 Sample Names'}
              </button>
            </div>
            <textarea
              rows={5}
              value={pasteText}
              onChange={(e) => {
                if (uploadedFileB64) clearUpload();
                setPasteText(e.target.value);
              }}
              placeholder={
                isFa
                  ? 'مثال:\nBank Sepah\nSahara Thunder\nشرکت تجاری نمونه...'
                  : 'Example (plain lines or CSV):\nBank Sepah\nSahara Thunder\nSepehr Energy Jahan\nNordic Clean Logistics GmbH'
              }
              className="w-full px-3 py-2 text-xs font-mono-tabular border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-600"
            />
          </div>
        </div>

        {/* Options + Action Button */}
        <div className="pt-4 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4">
          <label className="flex items-start gap-2.5 text-xs text-slate-700 cursor-pointer max-w-2xl">
            <input
              type="checkbox"
              checked={includeLiveWikiran}
              onChange={(e) => setIncludeLiveWikiran(e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-600"
            />
            <span>
              <strong className="text-slate-900 inline-flex items-center gap-1">
                <Globe className="w-3.5 h-3.5 text-sky-600" />
                {isFa
                  ? 'جستجوی زنده در ۳.۱ میلیون سند ویکی‌ایران + ذخیره دائمی آفلاین نتایج'
                  : 'Also check Live WikIran 3.1M+ Leak Archive & auto-save every hit offline'}
              </strong>{' '}
              <span className="text-slate-500">
                {isFa
                  ? '(حداکثر ۸۰ نام در هر نوبت به‌صورت آنلاین؛ بررسی آفلاین OFAC و OpenSanctions برای کل ۵٬۰۰۰ ردیف بدون محدودیت انجام می‌شود)'
                  : '(Screens up to 80 names live per run politely; offline OFAC + OpenSanctions + WikIran archives always screen all rows instantly.)'}
              </span>
            </span>
          </label>

          <button
            type="button"
            disabled={isScreening}
            onClick={handleRunScreening}
            className="px-6 py-3 text-xs sm:text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs cursor-pointer"
          >
            {isScreening ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>{isFa ? 'در حال غربالگری همه منابع...' : 'Screening All Datasets...'}</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>{isFa ? 'شروع غربالگری گروهی' : 'Run Batch Watchlist Screening'}</span>
              </>
            )}
          </button>
        </div>

        {errorMsg && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-800 font-medium">
            {errorMsg}
          </div>
        )}
      </section>

      {/* Screening Results & Risk Report Export */}
      {response?.ok && response.summary && (
        <section className="space-y-4">
          {/* Summary KPI Row + Report Download */}
          <div className="bg-white border-2 border-indigo-200 rounded-xl p-5 space-y-4 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  {isFa ? 'گزارش نتایج غربالگری ریسک' : 'Batch Compliance Screening Summary'}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  {isFa
                    ? `تعداد اسناد جدید ویکی‌ایران ذخیره‌شده به‌صورت آفلاین در این نوبت: ${response.summary.newly_cached_wikiran_docs}`
                    : `New WikIran leak documents automatically saved to your offline DB during this run: ${response.summary.newly_cached_wikiran_docs}`}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {response.reports?.xlsx_path && (
                  <a
                    href={`/api/watchlist/report/download?path=${encodeURIComponent(response.reports.xlsx_path)}`}
                    className="px-4 py-2.5 text-xs font-bold text-white bg-emerald-700 hover:bg-emerald-800 rounded-lg transition-colors inline-flex items-center gap-2 shadow-xs"
                  >
                    <FileSpreadsheet className="w-4 h-4" />
                    <span>{isFa ? 'دانلود گزارش ریسک اکسل (.xlsx)' : 'Download Risk Report Excel (.xlsx)'}</span>
                  </a>
                )}
                {response.reports?.csv_path && (
                  <a
                    href={`/api/watchlist/report/download?path=${encodeURIComponent(response.reports.csv_path)}`}
                    className="px-4 py-2.5 text-xs font-bold text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg transition-colors inline-flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>{isFa ? 'دانلود CSV' : 'Download CSV'}</span>
                  </a>
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                <div className="text-xs font-semibold text-slate-500">
                  {isFa ? 'کل موارد بررسی‌شده' : 'Total Screened'}
                </div>
                <div className="text-2xl font-bold font-mono-tabular text-slate-900 mt-1">
                  {response.summary.total_screened.toLocaleString()}
                </div>
              </div>
              <div className="bg-rose-50 border border-rose-200 rounded-lg p-3.5">
                <div className="text-xs font-bold text-rose-800 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>{isFa ? 'ریسک بالا (تحریمی)' : 'HIGH RISK (Sanctioned)'}</span>
                </div>
                <div className="text-2xl font-bold font-mono-tabular text-rose-900 mt-1">
                  {response.summary.high_risk_count.toLocaleString()}
                </div>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3.5">
                <div className="text-xs font-bold text-amber-800 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>{isFa ? 'ریسک متوسط (ویکی‌ایران)' : 'ELEVATED (WikIran Hit)'}</span>
                </div>
                <div className="text-2xl font-bold font-mono-tabular text-amber-900 mt-1">
                  {response.summary.elevated_risk_count.toLocaleString()}
                </div>
              </div>
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3.5">
                <div className="text-xs font-bold text-emerald-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>{isFa ? 'پاک (بدون تطابق)' : 'CLEAR (No Match)'}</span>
                </div>
                <div className="text-2xl font-bold font-mono-tabular text-emerald-900 mt-1">
                  {response.summary.clear_count.toLocaleString()}
                </div>
              </div>
            </div>
          </div>

          {/* Filter & Results Table */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
            <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-1.5">
                {(
                  [
                    ['ALL', isFa ? 'همه' : 'All'],
                    ['HIGH_RISK', isFa ? 'ریسک بالا' : 'High Risk'],
                    ['ELEVATED_RISK', isFa ? 'ریسک متوسط' : 'Elevated Risk'],
                    ['CLEAR', isFa ? 'پاک' : 'Clear'],
                  ] as const
                ).map(([key, lbl]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setRiskFilter(key)}
                    className={`px-3 py-1.5 text-xs font-bold rounded-md transition-colors cursor-pointer ${
                      riskFilter === key
                        ? 'bg-slate-900 text-white'
                        : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    {lbl}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                placeholder={isFa ? 'فیلتر در نتایج...' : 'Filter results by name, ref, or match...'}
                className="px-3 py-1.5 text-xs border border-slate-300 rounded-md w-64 max-w-full bg-white focus:outline-none focus:ring-2 focus:ring-indigo-600"
              />
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead className="bg-slate-100 text-slate-700 border-b border-slate-200">
                  <tr>
                    <th className="px-3.5 py-2.5 font-bold">#</th>
                    <th className="px-3.5 py-2.5 font-bold">{isFa ? 'نام ورودی / کد' : 'Input Name & Ref'}</th>
                    <th className="px-3.5 py-2.5 font-bold">{isFa ? 'سطح ریسک' : 'Risk Level'}</th>
                    <th className="px-3.5 py-2.5 font-bold text-center">OFAC</th>
                    <th className="px-3.5 py-2.5 font-bold text-center">OpenSanctions</th>
                    <th className="px-3.5 py-2.5 font-bold text-center">{isFa ? 'آفلاین ویکی‌ایران' : 'WikIran Offline'}</th>
                    <th className="px-3.5 py-2.5 font-bold text-center">{isFa ? 'آرشیو ۳.۱M' : 'WikIran 3.1M Live'}</th>
                    <th className="px-3.5 py-2.5 font-bold">{isFa ? 'مهم‌ترین تطابق' : 'Top Match'}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {filteredResults.map((row) => {
                    const isOpen = expandedRow === row.row_number;
                    return (
                      <React.Fragment key={row.row_number}>
                        <tr
                          onClick={() => setExpandedRow(isOpen ? null : row.row_number)}
                          className="hover:bg-slate-50 cursor-pointer transition-colors"
                        >
                          <td className="px-3.5 py-3 font-mono-tabular text-slate-500">
                            {row.row_number}
                          </td>
                          <td className="px-3.5 py-3">
                            <div className="font-bold text-slate-900">{row.name}</div>
                            <div className="text-[11px] text-slate-500 flex flex-wrap gap-2 mt-0.5">
                              {row.alias && <span>Alt: {row.alias}</span>}
                              {row.reference_id && (
                                <span className="font-mono-tabular text-indigo-700">
                                  {row.reference_id}
                                </span>
                              )}
                              {row.country && <span>{row.country}</span>}
                            </div>
                          </td>
                          <td className="px-3.5 py-3">
                            {row.risk_level === 'HIGH_RISK' ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-rose-100 text-rose-900 font-bold text-[11px]">
                                <ShieldAlert className="w-3.5 h-3.5" />
                                {isFa ? 'ریسک بالا (تحریمی)' : 'HIGH RISK'}
                              </span>
                            ) : row.risk_level === 'ELEVATED_RISK' ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-amber-100 text-amber-900 font-bold text-[11px]">
                                <AlertTriangle className="w-3.5 h-3.5" />
                                {isFa ? 'ریسک متوسط (ویکی‌ایران)' : 'ELEVATED RISK'}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-100 text-emerald-900 font-bold text-[11px]">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                {isFa ? 'پاک' : 'CLEAR'}
                              </span>
                            )}
                          </td>
                          <td className="px-3.5 py-3 text-center font-mono-tabular font-bold">
                            <span className={row.ofac_hits > 0 ? 'text-rose-700' : 'text-slate-400'}>
                              {row.ofac_hits}
                            </span>
                          </td>
                          <td className="px-3.5 py-3 text-center font-mono-tabular font-bold">
                            <span className={row.opensanctions_hits > 0 ? 'text-rose-700' : 'text-slate-400'}>
                              {row.opensanctions_hits}
                            </span>
                          </td>
                          <td className="px-3.5 py-3 text-center font-mono-tabular font-bold">
                            <span className={row.wikiran_offline_hits > 0 ? 'text-amber-700' : 'text-slate-400'}>
                              {row.wikiran_offline_hits}
                            </span>
                          </td>
                          <td className="px-3.5 py-3 text-center font-mono-tabular">
                            <span
                              className={
                                row.wikiran_live_total_int > 0
                                  ? 'text-sky-800 font-bold'
                                  : 'text-slate-400'
                              }
                            >
                              {row.wikiran_live_total_label}
                            </span>
                          </td>
                          <td className="px-3.5 py-3 max-w-xs">
                            {row.top_match_title ? (
                              <div className="space-y-0.5">
                                <div className="font-semibold text-slate-900 truncate">
                                  {row.top_match_title}
                                </div>
                                <div className="text-[11px] text-slate-500 truncate">
                                  {row.top_match_source}
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                        </tr>

                        {isOpen && (
                          <tr className="bg-slate-50/90">
                            <td colSpan={8} className="px-5 py-4 border-t border-slate-200">
                              {row.evidence_hits.length === 0 ? (
                                <div className="text-xs text-emerald-800 font-medium">
                                  {isFa
                                    ? 'هیچ تطابقی در OFAC، OpenSanctions و آرشیو ویکی‌ایران برای این نام یافت نشد.'
                                    : 'No matching sanctions or WikIran records found for this counterparty.'}
                                </div>
                              ) : (
                                <div className="space-y-2">
                                  <div className="text-xs font-bold text-slate-800">
                                    {isFa
                                      ? `شواهد و تطابق‌های یافت‌شده (${row.evidence_hits.length} مورد برتر):`
                                      : `Matched Compliance Evidence (${row.evidence_hits.length} top hits):`}
                                  </div>
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                                    {row.evidence_hits.map((hit, hIdx) => (
                                      <div
                                        key={`${row.row_number}-${hIdx}`}
                                        className="bg-white border border-slate-200 rounded-lg p-3 space-y-1"
                                      >
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-slate-900 text-white">
                                            {hit.source_bucket}
                                          </span>
                                          {hit.source_url && (
                                            <a
                                              href={hit.source_url}
                                              target="_blank"
                                              rel="noreferrer"
                                              onClick={(e) => e.stopPropagation()}
                                              className="text-[11px] text-indigo-700 hover:underline inline-flex items-center gap-1 font-semibold"
                                            >
                                              <span>{isFa ? 'لینک منبع' : 'Source'}</span>
                                              <ExternalLink className="w-3 h-3" />
                                            </a>
                                          )}
                                        </div>
                                        <div className="text-xs font-bold text-slate-900">
                                          {hit.title}
                                        </div>
                                        {hit.programs_or_leak && (
                                          <div className="text-[11px] text-indigo-800 font-medium">
                                            {hit.programs_or_leak}
                                          </div>
                                        )}
                                        {hit.snippet && (
                                          <div className="text-[11px] text-slate-600 line-clamp-2">
                                            {hit.snippet}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};
