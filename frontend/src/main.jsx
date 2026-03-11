import React, { useState, useEffect, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Search, Bell, Upload, FileText, AlertTriangle,
  CheckCircle, XCircle, TrendingUp,
  Shield, Plus, Trash2, Settings, LogOut, User
} from 'lucide-react';
import './index.css';

// ---------- API Configuration ----------

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:10000';

const api = {
  getKey() {
    return localStorage.getItem('skilledger_api_key');
  },

  async call(endpoint, options = {}) {
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.getKey() || '',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed (${response.status})`);
    }

    return response.json();
  },

  // Auth (no API key needed)
  async register(email, password, fullName, organization) {
    const response = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName, organization }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Registration failed');
    }
    return response.json();
  },

  async login(email, password) {
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Login failed');
    }
    return response.json();
  },

  // Protected endpoints
  verifyLicense(data) {
    return this.call('/api/verify/license', { method: 'POST', body: JSON.stringify(data) });
  },
  multiStateSearch(data) {
    return this.call('/api/verify/multi-state-search', { method: 'POST', body: JSON.stringify(data) });
  },
  getMonitors() {
    return this.call('/api/monitor/my-monitors');
  },
  deleteMonitor(monitorId) {
    return this.call(`/api/monitor/${monitorId}`, { method: 'DELETE' });
  },
  getComplianceDashboard() {
    return this.call('/api/audit/compliance-dashboard');
  },
  async uploadBulkCSV(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${API_URL}/api/bulk/upload`, {
      method: 'POST',
      headers: { 'X-API-Key': this.getKey() || '' },
      body: formData,
    });
    if (!response.ok) throw new Error('Upload failed');
    return response.json();
  },
};

// ---------- Toast ----------

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const bg = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';

  return (
    <div className={`fixed top-4 right-4 ${bg} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-slide-in`}>
      {message}
    </div>
  );
}

// ---------- Login / Register Page ----------

function AuthPage({ onAuth }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ email: '', password: '', fullName: '', organization: '' });

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      let result;
      if (mode === 'login') {
        result = await api.login(form.email, form.password);
      } else {
        result = await api.register(form.email, form.password, form.fullName, form.organization);
      }

      // Store API key and user info
      localStorage.setItem('skilledger_api_key', result.api_key);
      localStorage.setItem('skilledger_user', JSON.stringify({
        email: result.email,
        fullName: result.full_name,
        organization: result.organization,
      }));

      onAuth(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 w-full max-w-md p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-blue-600">SkillLedger</h1>
          <p className="text-gray-500 mt-1">Professional License Verification</p>
        </div>

        {/* Tabs */}
        <div className="flex rounded-lg border border-gray-200 p-1 mb-6">
          <button
            onClick={() => { setMode('login'); setError(''); }}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
              mode === 'login' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => { setMode('register'); setError(''); }}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition ${
              mode === 'register' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input
                  type="text"
                  value={form.fullName}
                  onChange={set('fullName')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Jane Doe"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Organization</label>
                <input
                  type="text"
                  value={form.organization}
                  onChange={set('organization')}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Acme Staffing"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={set('email')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="you@company.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={set('password')}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="••••••••"
              required
              minLength={8}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold transition"
          >
            {loading
              ? (mode === 'login' ? 'Logging in...' : 'Creating account...')
              : (mode === 'login' ? 'Login' : 'Create Account')}
          </button>
        </form>
      </div>
    </div>
  );
}

// ---------- Main App ----------

function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('skilledger_api_key'));
  const [currentView, setCurrentView] = useState('dashboard');
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
  }, []);

  const handleAuth = (result) => {
    setAuthed(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('skilledger_api_key');
    localStorage.removeItem('skilledger_user');
    setAuthed(false);
  };

  if (!authed) {
    return <AuthPage onAuth={handleAuth} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      <Sidebar currentView={currentView} setCurrentView={setCurrentView} onLogout={handleLogout} />

      <div className="ml-64 p-8">
        <Header onLogout={handleLogout} setCurrentView={setCurrentView} />

        {currentView === 'dashboard'  && <Dashboard    showToast={showToast} />}
        {currentView === 'verify'     && <VerifyPage   showToast={showToast} />}
        {currentView === 'multistate' && <MultiStatePage showToast={showToast} />}
        {currentView === 'monitoring' && <MonitoringPage showToast={showToast} />}
        {currentView === 'bulk'       && <BulkUploadPage showToast={showToast} />}
        {currentView === 'compliance' && <CompliancePage showToast={showToast} />}
        {currentView === 'settings'   && <SettingsPage  showToast={showToast} />}
      </div>
    </div>
  );
}

// ---------- Sidebar ----------

function Sidebar({ currentView, setCurrentView, onLogout }) {
  const navItems = [
    { id: 'dashboard',  icon: TrendingUp, label: 'Dashboard' },
    { id: 'verify',     icon: Search,     label: 'Verify License' },
    { id: 'multistate', icon: Shield,     label: 'Multi-State Search' },
    { id: 'monitoring', icon: Bell,       label: 'Monitoring' },
    { id: 'bulk',       icon: Upload,     label: 'Bulk Upload' },
    { id: 'compliance', icon: FileText,   label: 'Compliance' },
  ];

  const user = JSON.parse(localStorage.getItem('skilledger_user') || '{}');

  return (
    <div className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 p-6 flex flex-col">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-blue-600">SkillLedger</h1>
        <p className="text-sm text-gray-500">License Verification</p>
      </div>

      <nav className="space-y-2 flex-1">
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

      {/* User info + logout */}
      <div className="border-t border-gray-200 pt-4 mt-4">
        <div className="flex items-center space-x-3 mb-3 px-2">
          <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
            <User size={16} className="text-blue-600" />
          </div>
          <div className="text-sm overflow-hidden">
            <div className="font-medium text-gray-900 truncate">{user.fullName || 'User'}</div>
            <div className="text-gray-500 truncate text-xs">{user.email}</div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center space-x-3 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition"
        >
          <LogOut size={18} />
          <span className="text-sm">Logout</span>
        </button>
      </div>
    </div>
  );
}

// ---------- Header ----------

function Header({ setCurrentView }) {
  const user = JSON.parse(localStorage.getItem('skilledger_user') || '{}');

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">
            Welcome back{user.fullName ? `, ${user.fullName.split(' ')[0]}` : ''}!
          </h2>
          <p className="text-gray-500">Manage your license verifications</p>
        </div>
        <button
          onClick={() => setCurrentView('settings')}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}

// ---------- Dashboard ----------

function Dashboard({ showToast }) {
  const [stats, setStats] = useState({
    totalVerifications: 0,
    activeMonitors: 0,
    expiringSoon: 0,
    complianceRate: 100,
  });

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
    { label: 'Total Verifications', value: stats.totalVerifications,              icon: CheckCircle,   color: 'blue'   },
    { label: 'Active Monitors',     value: stats.activeMonitors,                  icon: Bell,          color: 'green'  },
    { label: 'Expiring Soon',       value: stats.expiringSoon,                    icon: AlertTriangle, color: 'yellow' },
    { label: 'Compliance Rate',     value: `${stats.complianceRate.toFixed(1)}%`, icon: Shield,        color: 'purple' },
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

// ---------- Verify License ----------

function VerifyPage({ showToast }) {
  const [formData, setFormData] = useState({ license_number: '', state_code: '', license_type: 'RN' });
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
            <label className="block text-sm font-medium text-gray-700 mb-2">License Number</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-2">State</label>
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
              <label className="block text-sm font-medium text-gray-700 mb-2">License Type</label>
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
        <div className={`p-6 rounded-lg border-2 ${result.verified ? 'border-green-500 bg-green-50' : 'border-red-500 bg-red-50'}`}>
          <div className="flex items-center space-x-3 mb-4">
            {result.verified ? <CheckCircle className="text-green-600" size={32} /> : <XCircle className="text-red-600" size={32} />}
            <h4 className="text-xl font-bold">{result.verified ? 'License Verified ✓' : 'License Not Found'}</h4>
          </div>
          {result.verified && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><span className="font-semibold">Status:</span> {result.status}</div>
              <div><span className="font-semibold">Type:</span> {result.license_type}</div>
              <div><span className="font-semibold">Expires:</span> {result.expiration_date}</div>
              <div><span className="font-semibold">Discipline:</span> {result.discipline_record ? 'Yes' : 'None'}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------- Multi-State Search ----------

function MultiStatePage({ showToast }) {
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [formData, setFormData] = useState({ first_name: '', last_name: '', states: ['AZ', 'CA', 'TX', 'FL', 'NY'] });

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
              <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
              <input type="text" value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg" placeholder="Jane" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
              <input type="text" value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg" placeholder="Doe" required />
            </div>
          </div>
          <button type="submit" disabled={searching}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold">
            {searching ? 'Searching All States...' : 'Search 5 States'}
          </button>
        </form>
      </div>

      {results && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <div className="font-semibold text-blue-900">Searched {results.total_states_searched} states in {results.search_duration_ms}ms</div>
            <div className="text-blue-700">Found {results.total_licenses_found} active licenses</div>
          </div>
          {results.results.map((result, i) => (
            <div key={i} className={`p-4 rounded-lg border ${result.status === 'success' && result.license ? 'border-green-300 bg-green-50' : 'border-gray-300 bg-gray-50'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-semibold">{result.state}</span>
                  {result.license && <span className="ml-4 text-sm">License: {result.license.license_number} | Expires: {result.license.expiration_date}</span>}
                  {result.status === 'no_match' && <span className="ml-4 text-sm text-gray-500">No license found</span>}
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

// ---------- Monitoring ----------

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

  useEffect(() => { loadMonitors(); }, [loadMonitors]);

  const handleDelete = async (monitorId) => {
    try {
      await api.deleteMonitor(monitorId);
      showToast('Monitor removed', 'success');
      loadMonitors();
    } catch (error) {
      showToast(error.message, 'error');
    }
  };

  if (loading) return <div className="text-center py-12">Loading monitors...</div>;

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold">License Monitoring</h3>
        <button className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <Plus size={20} /><span>Add Monitor</span>
        </button>
      </div>

      {monitors.length === 0 ? (
        <div className="bg-white p-12 rounded-lg shadow-sm border border-gray-200 text-center">
          <Bell size={48} className="mx-auto text-gray-400 mb-4" />
          <h4 className="text-xl font-semibold mb-2">No monitors yet</h4>
          <p className="text-gray-500 mb-6">Start monitoring licenses to get expiration alerts</p>
          <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Add Your First Monitor</button>
        </div>
      ) : (
        <div className="space-y-4">
          {monitors.map((monitor) => (
            <div key={monitor.monitor_id} className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="font-semibold text-lg">{monitor.professional_name || 'Professional'}</h4>
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      monitor.priority === 'critical' ? 'bg-red-100 text-red-800' :
                      monitor.priority === 'high'     ? 'bg-yellow-100 text-yellow-800' :
                                                        'bg-green-100 text-green-800'}`}>
                      {monitor.priority}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 space-x-4">
                    <span>License: {monitor.license_number}</span>
                    <span>State: {monitor.state}</span>
                    <span>Type: {monitor.type}</span>
                    <span>Expires: {monitor.expires}</span>
                    <span className="font-semibold">{monitor.days_until_expiration} days remaining</span>
                  </div>
                </div>
                <button onClick={() => handleDelete(monitor.monitor_id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
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

// ---------- Bulk Upload ----------

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
              <span className="text-gray-600">{file ? file.name : 'Click to upload CSV file'}</span>
              <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0])} className="hidden" />
            </label>
          </div>
          <button type="submit" disabled={!file || uploading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold">
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

// ---------- Compliance Dashboard ----------

function CompliancePage({ showToast }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getComplianceDashboard()
      .then(setData)
      .catch(() => showToast('Error loading compliance data', 'error'))
      .finally(() => setLoading(false));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) return <div className="text-center py-12">Loading compliance dashboard...</div>;
  if (!data)   return <div className="text-center py-12 text-gray-500">No data available</div>;

  return (
    <div className="max-w-6xl space-y-6">
      <h3 className="text-2xl font-bold">Compliance Dashboard</h3>

      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
        <h4 className="font-semibold text-lg mb-4">Summary - {data.period}</h4>
        <div className="grid grid-cols-4 gap-4">
          <div><div className="text-3xl font-bold text-blue-600">{data.summary.total_verifications}</div><div className="text-sm text-gray-500">Total Verifications</div></div>
          <div><div className="text-3xl font-bold text-green-600">{data.summary.unique_candidates}</div><div className="text-sm text-gray-500">Unique Candidates</div></div>
          <div><div className="text-3xl font-bold text-purple-600">{data.summary.compliance_rate}</div><div className="text-sm text-gray-500">Compliance Rate</div></div>
          <div><div className="text-3xl font-bold text-red-600">{data.summary.issues_found}</div><div className="text-sm text-gray-500">Issues Found</div></div>
        </div>
      </div>

      {data.upcoming_expirations?.length > 0 && (
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
                  <div className="font-semibold text-yellow-700">{item.days_remaining} days</div>
                  <div className="text-sm text-gray-600">{item.expires}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.risk_alerts?.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Risk Alerts</h4>
          <div className="space-y-3">
            {data.risk_alerts.map((alert, i) => (
              <div key={i} className="flex items-start space-x-3 p-3 bg-red-50 rounded">
                <AlertTriangle className="text-red-600 flex-shrink-0" size={20} />
                <div className="flex-1">
                  <div className="font-semibold text-red-900">{alert.alert}</div>
                  <div className="text-sm text-red-700">{alert.candidate} - {alert.license}</div>
                  <div className="text-sm text-red-600 mt-1">Action: {alert.action_required}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- Settings Page ----------

function SettingsPage({ showToast }) {
  const storedUser = JSON.parse(localStorage.getItem('skilledger_user') || '{}');

  const [form, setForm] = useState({
    fullName:     storedUser.fullName     || '',
    organization: storedUser.organization || '',
    email:        storedUser.email        || '',
    website:      storedUser.website      || '',
    phone:        storedUser.phone        || '',
    address:      storedUser.address      || '',
  });
  const [logo, setLogo]       = useState(storedUser.logo || null);
  const [saving, setSaving]   = useState(false);
  const [preview, setPreview] = useState(storedUser.logo || null);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleLogoChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      showToast('Logo must be under 2MB', 'error');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setPreview(reader.result);
      setLogo(reader.result);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveLogo = () => {
    setPreview(null);
    setLogo(null);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      // Save to localStorage (extend with API call when backend supports it)
      const updated = { ...form, logo };
      localStorage.setItem('skilledger_user', JSON.stringify(updated));
      showToast('Settings saved successfully!', 'success');
    } catch (err) {
      showToast('Error saving settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h3 className="text-2xl font-bold mb-6">Organization Settings</h3>

      <form onSubmit={handleSave} className="space-y-6">

        {/* Logo */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Organization Logo</h4>
          <div className="flex items-center space-x-6">
            <div className="w-24 h-24 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden bg-gray-50">
              {preview ? (
                <img src={preview} alt="Logo" className="w-full h-full object-contain" />
              ) : (
                <div className="text-center">
                  <Upload size={24} className="mx-auto text-gray-400 mb-1" />
                  <span className="text-xs text-gray-400">No logo</span>
                </div>
              )}
            </div>
            <div className="space-y-2">
              <label className="block">
                <span className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer text-sm font-medium">
                  Upload Logo
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleLogoChange}
                  className="hidden"
                />
              </label>
              {preview && (
                <button
                  type="button"
                  onClick={handleRemoveLogo}
                  className="block text-sm text-red-600 hover:underline"
                >
                  Remove logo
                </button>
              )}
              <p className="text-xs text-gray-500">PNG, JPG up to 2MB</p>
            </div>
          </div>
        </div>

        {/* Organization Details */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Organization Details</h4>
          <div className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Organization Name</label>
              <input
                type="text"
                value={form.organization}
                onChange={set('organization')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Acme Staffing"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Website</label>
              <input
                type="url"
                value={form.website}
                onChange={set('website')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="https://yourcompany.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
              <input
                type="tel"
                value={form.phone}
                onChange={set('phone')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="+1 (555) 000-0000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Address</label>
              <textarea
                value={form.address}
                onChange={set('address')}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="123 Main St, Phoenix, AZ 85001"
              />
            </div>
          </div>
        </div>

        {/* Personal Details */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">Your Details</h4>
          <div className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
              <input
                type="text"
                value={form.fullName}
                onChange={set('fullName')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Jane Doe"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={set('email')}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="you@company.com"
                disabled
              />
              <p className="text-xs text-gray-400 mt-1">Email cannot be changed</p>
            </div>
          </div>
        </div>

        {/* API Key */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
          <h4 className="font-semibold text-lg mb-4">API Key</h4>
          <div className="bg-gray-50 p-3 rounded-lg font-mono text-sm text-gray-700 break-all">
            {localStorage.getItem('skilledger_api_key') || 'No API key found'}
          </div>
          <p className="text-xs text-gray-400 mt-2">Include this in the <code>X-API-Key</code> header for direct API calls</p>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}

// ---------- Render ----------

const root = createRoot(document.getElementById('root'));
root.render(<App />);
