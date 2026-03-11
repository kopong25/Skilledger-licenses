import React, { useState, useEffect, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Search, Bell, Upload, FileText, AlertTriangle,
  CheckCircle, XCircle, Clock, TrendingUp, Users,
  Shield, Eye, Download, Plus, Trash2, Settings
} from 'lucide-react';
import './index.css';

// API Configuration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:10000';
const API_KEY = import.meta.env.VITE_API_KEY;

// API Service
const api = {
  async call(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed (${response.status})`);
    }

    return response.json();
  },

  verifyLicense(data) {
    return this.call('/api/verify/license', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  multiStateSearch(data) {
    return this.call('/api/verify/multi-state-search', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getMonitors() {
    return this.call('/api/monitor/my-monitors');
  },

  subscribeMonitor(data) {
    return this.call('/api/monitor/subscribe', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  deleteMonitor(monitorId) {
    return this.call(`/api/monitor/${monitorId}`, {
      method: 'DELETE',
    });
  },

  getComplianceDashboard() {
    return this.call('/api/audit/compliance-dashboard');
  },

  async uploadBulkCSV(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/api/bulk/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': API_KEY,
      },
      body: formData,
    });

    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },
};

// Toast Notification Component
function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bgColor =
    type === 'success' ? 'bg-green-500' :
    type === 'error'   ? 'bg-red-500'   :
                         'bg-blue-500';

  return (
    <div className={`fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-slide-in`}>
      {message}
    </div>
  );
}

// Main App Component
function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [toast, setToast] = useState(null);

  // FIX: useCallback gives showToast a stable reference so it never
  // triggers useEffect re-runs in child components.
  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      <Sidebar currentView={currentView} setCurrentView={setCurrentView} />

      <div className="ml-64 p-8">
        <Header />

        {currentView === 'dashboard'   && <Dashboard    showToast={showToast} />}
        {currentView === 'verify'      && <VerifyPage   showToast={showToast} />}
        {currentView === 'multistate'  && <MultiStatePage showToast={showToast} />}
        {currentView === 'monitoring'  && <MonitoringPage showToast={showToast} />}
        {currentView === 'bulk'        && <BulkUploadPage showToast={showToast} />}
        {currentView === 'compliance'  && <CompliancePage showToast={showToast} />}
      </div>
    </div>
  );
}

// Sidebar Navigation
function Sidebar({ currentView, setCurrentView }) {
  const navItems = [
    { id: 'dashboard',  icon: TrendingUp, label: 'Dashboard' },
    { id: 'verify',     icon: Search,     label: 'Verify License' },
    { id: 'multistate', icon: Shield,     label: 'Multi-State Search' },
    { id: 'monitoring', icon: Bell,       label: 'Monitoring' },
    { id: 'bulk',       icon: Upload,     label: 'Bulk Upload' },
    { id: 'compliance', icon: FileText,   label: 'Compliance' },
  ];

  return (
    <div className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-blue-600">SkillLedger</h1>
        <p className="text-sm text-gray-500">License Verification</p>
      </div>

      <nav className="space-y-2">
        {navItems.map(item => (
          <button
            key={item.id}
            onClick={() => setCurrentView(item.id)}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${
              currentView === item.id
                ? 'bg-blue-50 text-blue-600'
                : 'text-gray-700 hover:bg-gray-50'
            }`}
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}

// Header Component
function Header() {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Welcome back!</h2>
          <p className="text-gray-500">Manage your license verifications</p>
        </div>
        <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}

// Dashboard Page
function Dashboard({ showToast }) {
  const [stats, setStats] = useState({
    totalVerifications: 0,
    activeMonitors: 0,
    expiringSoon: 0,
    complianceRate: 100,
  });

  // FIX: empty dep array — runs once on mount only.
  // showToast is intentionally excluded; it's stable via useCallback
  // but including it here could still cause loops in edge cases.
  useEffect(() => {
    api.getComplianceDashboard()
      .then(data => {
        setStats({
          totalVerifications: data.summary.total_verifications || 0,
          activeMonitors:     data.summary.unique_candidates   || 0,
          expiringSoon:       data.upcoming_expirations?.length || 0,
          complianceRate:     parseFloat(data.summary.compliance_rate) || 100,
        });
      })
      .catch(() => showToast('Error loading dashboard', 'error'));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const statCards = [
    { label: 'Total Verifications', value: stats.totalVerifications,              icon: CheckCircle,  color: 'blue'   },
    { label: 'Active Monitors',     value: stats.activeMonitors,                  icon: Bell,         color: 'green'  },
    { label: 'Expiring Soon',       value: stats.expiringSoon,                    icon: AlertTriangle,color: 'yellow' },
    { label: 'Compliance Rate',     value: `${stats.complianceRate.toFixed(1)}%`, icon: Shield,       color: 'purple' },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-4 gap-6">
        {statCards.map((stat, i) => (
          <div key={i} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <stat.icon className={`text-${stat.color}-500`} size={24} />
            </div>
            <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
            <div className="text-sm text-gray-500">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h3 className="text-xl font-bold mb-4">Quick Actions</h3>
        <div className="grid grid-cols-3 gap-4">
          <button className="p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition">
            <Search size={32} className="mx-auto mb-2 text-blue-600" />
            <div className="font-semibold">Verify License</div>
            <div className="text-sm text-gray-500">Single verification</div>
          </button>
          <button className="p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition">
            <Upload size={32} className="mx-auto mb-2 text-blue-600" />
            <div className="font-semibold">Bulk Upload</div>
            <div className="text-sm text-gray-500">CSV verification</div>
          </button>
          <button className="p-6 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition">
            <Bell size={32} className="mx-auto mb-2 text-blue-600" />
            <div className="font-semibold">Add Monitor</div>
            <div className="text-sm text-gray-500">Track expiration</div>
          </button>
        </div>
      </div>
    </div>
  );
}

// Verify License Page
function VerifyPage({ showToast }) {
  const [formData, setFormData] = useState({
    license_number: '',
    state_code: '',
    license_type: 'RN',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const data = await api.verifyLicense(formData);
      setResult(data);
      showToast('License verified successfully!', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <h3 className="text-2xl font-bold mb-6">Verify Single License</h3>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              License Number
            </label>
            <input
              type="text"
              value={formData.license_number}
              onChange={(e) => setFormData({ ...formData, license_number: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="123456"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                State
              </label>
              <select
                value={formData.state_code}
                onChange={(e) => setFormData({ ...formData, state_code: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="">Select State</option>
                <option value="AZ">Arizona</option>
                <option value="CA">California</option>
                <option value="TX">Texas</option>
                <option value="FL">Florida</option>
                <option value="NY">New York</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                License Type
              </label>
              <select
                value={formData.license_type}
                onChange={(e) => setFormData({ ...formData, license_type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="RN">RN</option>
                <option value="LPN">LPN</option>
                <option value="CDL">CDL</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
          >
            {loading ? 'Verifying...' : 'Verify License'}
          </button>
        </form>
      </div>

      {result && (
        <div className={`p-6 rounded-lg border-2 ${
          result.verified ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'
        }`}>
          <div className="flex items-center space-x-3 mb-4">
            {result.verified ? (
              <CheckCircle className="text-green-600" size={32} />
            ) : (
              <XCircle className="text-red-600" size={32} />
            )}
            <h4 className="text-xl font-bold">
              {result.verified ? 'License Verified ✓' : 'License Not Found'}
            </h4>
          </div>

          {result.verified && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="font-semibold">Status:</span> {result.status}</div>
              <div><span className="font-semibold">Type:</span> {result.license_type}</div>
              <div><span className="font-semibold">Expires:</span> {result.expiration_date}</div>
              <div>
                <span className="font-semibold">Discipline:</span>{' '}
                {result.discipline_record ? 'Yes' : 'None'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Multi-State Search Page
function MultiStatePage({ showToast }) {
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    states: ['AZ', 'CA', 'TX', 'FL', 'NY'],
  });

  const handleSearch = async (e) => {
    e.preventDefault();
    setSearching(true);
    setResults(null);

    try {
      const data = await api.multiStateSearch(formData);
      setResults(data);
      showToast(`Found ${data.total_licenses_found} licenses`, 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="max-w-6xl">
      <h3 className="text-2xl font-bold mb-6">Multi-State License Search</h3>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                First Name
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="Jane"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Last Name
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                placeholder="Doe"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={searching}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
          >
            {searching ? 'Searching All States...' : 'Search 5 States'}
          </button>
        </form>
      </div>

      {results && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <div className="font-semibold text-blue-900">
              Searched {results.total_states_searched} states in {results.search_duration_ms}ms
            </div>
            <div className="text-blue-700">
              Found {results.total_licenses_found} active licenses
            </div>
          </div>

          {results.results.map((result, i) => (
            <div
              key={i}
              className={`p-4 rounded-lg border ${
                result.status === 'success' && result.license
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-300 bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold">{result.state}</span>
                  {result.license && (
                    <span className="ml-4 text-sm">
                      License: {result.license.license_number} |
                      Expires: {result.license.expiration_date}
                    </span>
                  )}
                  {result.status === 'no_match' && (
                    <span className="ml-4 text-sm text-gray-500">No license found</span>
                  )}
                </div>
                {result.license && <CheckCircle className="text-green-600" size={20} />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Monitoring Page
function MonitoringPage({ showToast }) {
  const [monitors, setMonitors] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadMonitors = useCallback(async () => {
    try {
      const data = await api.getMonitors();
      setMonitors(data.monitors || []);
    } catch (error) {
      showToast('Error loading monitors', 'error');
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadMonitors();
  }, [loadMonitors]);

  const handleDelete = async (monitorId) => {
    try {
      await api.deleteMonitor(monitorId);
      showToast('Monitor removed', 'success');
      loadMonitors();
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  if (loading) {
    return <div className="text-center py-12">Loading monitors...</div>;
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold">License Monitoring</h3>
        <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus size={20} />
          <span>Add Monitor</span>
        </button>
      </div>

      {monitors.length === 0 ? (
        <div className="bg-white p-12 rounded-lg shadow-sm border border-gray-200 text-center">
          <Bell size={48} className="mx-auto text-gray-400 mb-4" />
          <h4 className="text-xl font-semibold mb-2">No monitors yet</h4>
          <p className="text-gray-500 mb-6">
            Start monitoring licenses to get expiration alerts
          </p>
          <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Add Your First Monitor
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {monitors.map((monitor) => (
            <div
              key={monitor.monitor_id}
              className="bg-white p-6 rounded-lg shadow-sm border border-gray-200"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="font-semibold text-lg">
                      {monitor.professional_name || 'Professional'}
                    </h4>
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      monitor.priority === 'critical'
                        ? 'bg-red-100 text-red-800'
                        : monitor.priority === 'high'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {monitor.priority}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-x-4">
                    <span>License: {monitor.license_number}</span>
                    <span>State: {monitor.state}</span>
                    <span>Type: {monitor.type}</span>
                    <span>Expires: {monitor.expires}</span>
                    <span className="font-semibold">
                      {monitor.days_until_expiration} days remaining
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(monitor.monitor_id)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Bulk Upload Page
function BulkUploadPage({ showToast }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    try {
      const data = await api.uploadBulkCSV(file);
      setResult(data);
      showToast('Upload successful!', 'success');
    } catch (error) {
      showToast(error.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <h3 className="text-2xl font-bold mb-6">Bulk License Verification</h3>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 mb-6">
        <div className="mb-6">
          <h4 className="font-semibold mb-2">CSV Format</h4>
          <div className="bg-gray-50 p-4 rounded font-mono text-sm">
            license_number,state,candidate_name<br />
            123456,AZ,Jane Doe<br />
            789012,CA,John Smith
          </div>
        </div>

        <form onSubmit={handleUpload}>
          <div className="mb-4">
            <label className="block w-full px-6 py-12 border-2 border-dashed border-gray-300 rounded-lg text-center cursor-pointer hover:border-blue-500">
              <Upload size={48} className="mx-auto text-gray-400 mb-2" />
              <span className="text-gray-600">
                {file ? file.name : 'Click to upload CSV file'}
              </span>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files[0])}
                className="hidden"
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={!file || uploading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
          >
            {uploading ? 'Uploading...' : 'Upload and Verify'}
          </button>
        </form>
      </div>

      {result && (
        <div className="bg-green-50 border border-green-200 p-6 rounded-lg">
          <h4 className="font-semibold text-green-900 mb-2">Upload Successful!</h4>
          <div className="text-green-700">
            Job ID: {result.job_id}<br />
            Total licenses: {result.total_licenses}<br />
            Status: {result.status}
          </div>
        </div>
      )}
    </div>
  );
}

// Compliance Dashboard Page
function CompliancePage({ showToast }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // FIX: empty dep array — runs once on mount only, no infinite loop.
  useEffect(() => {
    api.getComplianceDashboard()
      .then(setData)
      .catch(() => showToast('Error loading compliance data', 'error'))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return <div className="text-center py-12">Loading compliance dashboard...</div>;
  }

  if (!data) {
    return <div className="text-center py-12 text-gray-500">No data available</div>;
  }

  return (
    <div className="max-w-6xl space-y-6">
      <h3 className="text-2xl font-bold">Compliance Dashboard</h3>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h4 className="font-semibold text-lg mb-4">Summary - {data.period}</h4>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="text-3xl font-bold text-blue-600">
              {data.summary.total_verifications}
            </div>
            <div className="text-sm text-gray-500">Total Verifications</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600">
              {data.summary.unique_candidates}
            </div>
            <div className="text-sm text-gray-500">Unique Candidates</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600">
              {data.summary.compliance_rate}
            </div>
            <div className="text-sm text-gray-500">Compliance Rate</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-red-600">
              {data.summary.issues_found}
            </div>
            <div className="text-sm text-gray-500">Issues Found</div>
          </div>
        </div>
      </div>

      {data.upcoming_expirations && data.upcoming_expirations.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Upcoming Expirations</h4>
          <div className="space-y-3">
            {data.upcoming_expirations.slice(0, 5).map((item, i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-yellow-50 rounded">
                <div>
                  <div className="font-semibold">{item.candidate}</div>
                  <div className="text-sm text-gray-600">{item.license}</div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-yellow-700">
                    {item.days_remaining} days
                  </div>
                  <div className="text-sm text-gray-600">{item.expires}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.risk_alerts && data.risk_alerts.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Risk Alerts</h4>
          <div className="space-y-3">
            {data.risk_alerts.map((alert, i) => (
              <div key={i} className="flex items-start space-x-3 p-3 bg-red-50 rounded">
                <AlertTriangle className="text-red-600 flex-shrink-0" size={20} />
                <div className="flex-1">
                  <div className="font-semibold text-red-900">{alert.alert}</div>
                  <div className="text-sm text-red-700">
                    {alert.candidate} - {alert.license}
                  </div>
                  <div className="text-sm text-red-600 mt-1">
                    Action: {alert.action_required}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Render App
const root = createRoot(document.getElementById('root'));
root.render(<App />);
