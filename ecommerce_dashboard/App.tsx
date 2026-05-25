
import React, { useState, useMemo } from 'react';
import { initialData } from './mockData';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  PieChart, Pie, Cell, AreaChart, Area, LineChart, Line, ScatterChart, Scatter, ZAxis
} from 'recharts';
import { 
  Users, MapPin, CheckCircle, XCircle, Tag, Filter, Download, 
  LayoutDashboard, TrendingUp, AlertTriangle, Layers
} from 'lucide-react';

const COLORS = ['#0078D4', '#2B88D8', '#107C10', '#D83B01', '#A4262C', '#5C2D91', '#00188F', '#00B294'];

const App: React.FC = () => {
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  const [validityFilter, setValidityFilter] = useState<'all' | 'valid' | 'invalid'>('all');

  const filteredRaw = useMemo(() => {
    return initialData.pedagang_per_lokasi_all.filter(p => {
      const locMatch = selectedLocations.length === 0 || selectedLocations.includes(p.lokasi);
      const valMatch = validityFilter === 'all' || 
                       (validityFilter === 'valid' && p.is_valid) || 
                       (validityFilter === 'invalid' && !p.is_valid);
      return locMatch && valMatch;
    });
  }, [selectedLocations, validityFilter]);

  const dashboardStats = useMemo(() => {
    const total = filteredRaw.length;
    const valid = filteredRaw.filter(p => p.is_valid).length;
    const locations = Array.from(new Set(filteredRaw.map(p => p.lokasi))).length;
    const categories = Array.from(new Set(filteredRaw.map(p => p.kategori))).length;

    return {
      total,
      valid,
      invalid: total - valid,
      locations,
      categories,
      validityPct: total > 0 ? ((valid / total) * 100).toFixed(1) : '0'
    };
  }, [filteredRaw]);

  // Derived charts based on filtered data
  const chartData_SebaranLokasi = useMemo(() => {
    const map = new Map();
    filteredRaw.forEach(p => map.set(p.lokasi, (map.get(p.lokasi) || 0) + 1));
    return Array.from(map.entries()).map(([lokasi, jumlah]) => ({ lokasi, jumlah })).sort((a, b) => b.jumlah - a.jumlah);
  }, [filteredRaw]);

  const chartData_SebaranKategori = useMemo(() => {
    const map = new Map();
    filteredRaw.forEach(p => map.set(p.kategori, (map.get(p.kategori) || 0) + 1));
    return Array.from(map.entries()).map(([kategori, jumlah]) => ({ kategori, jumlah }));
  }, [filteredRaw]);

  const chartData_AlasanTidakValid = useMemo(() => {
    const map = new Map();
    filteredRaw.filter(p => !p.is_valid).forEach(p => {
      map.set(p.alasan_tidak_valid, (map.get(p.alasan_tidak_valid) || 0) + 1);
    });
    return Array.from(map.entries()).map(([alasan, jumlah]) => ({ alasan, jumlah }));
  }, [filteredRaw]);

  const toggleLocation = (loc: string) => {
    setSelectedLocations(prev => 
      prev.includes(loc) ? prev.filter(l => l !== loc) : [...prev, loc]
    );
  };

  const allLocations = Array.from(new Set(initialData.pedagang_per_lokasi_all.map(p => p.lokasi))).sort();

  return (
    <div className="flex h-screen bg-gray-50 text-slate-800">
      {/* Sidebar Filters */}
      <aside className="w-72 bg-white border-r border-gray-200 flex flex-col shadow-sm">
        <div className="p-6 border-b border-gray-100 bg-slate-900 text-white">
          <div className="flex items-center gap-2 mb-1">
            <LayoutDashboard size={24} className="text-blue-400" />
            <h1 className="text-xl font-bold tracking-tight">Supervisor BI</h1>
          </div>
          <p className="text-xs text-slate-400 uppercase font-semibold">Monitoring Dashboard</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-500 uppercase mb-4">
              <MapPin size={16} /> Filter Lokasi
            </h3>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
              {allLocations.map(loc => (
                <label key={loc} className="flex items-center gap-3 group cursor-pointer hover:bg-gray-50 p-1.5 rounded transition-all">
                  <input 
                    type="checkbox" 
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    checked={selectedLocations.includes(loc)}
                    onChange={() => toggleLocation(loc)}
                  />
                  <span className={`text-sm ${selectedLocations.includes(loc) ? 'text-blue-700 font-medium' : 'text-slate-600'}`}>
                    {loc}
                  </span>
                </label>
              ))}
            </div>
            {selectedLocations.length > 0 && (
              <button 
                onClick={() => setSelectedLocations([])}
                className="mt-4 text-xs text-blue-600 hover:text-blue-800 font-medium underline"
              >
                Clear Selections
              </button>
            )}
          </div>

          <div>
            <h3 className="flex items-center gap-2 text-sm font-bold text-slate-500 uppercase mb-4">
              <CheckCircle size={16} /> Status Validasi
            </h3>
            <div className="space-y-3">
              {[
                { id: 'all', label: 'Semua Status', icon: <Layers size={14}/> },
                { id: 'valid', label: 'Valid Saja', icon: <CheckCircle size={14}/> },
                { id: 'invalid', label: 'Tidak Valid Saja', icon: <XCircle size={14}/> }
              ].map(opt => (
                <button
                  key={opt.id}
                  onClick={() => setValidityFilter(opt.id as any)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                    validityFilter === opt.id 
                      ? 'bg-blue-600 text-white shadow-md font-semibold' 
                      : 'bg-white text-slate-600 hover:bg-gray-100 border border-gray-200'
                  }`}
                >
                  {opt.icon}
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-gray-100 bg-gray-50">
          <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-800 text-white rounded hover:bg-slate-700 transition-colors text-sm font-medium">
            <Download size={16} /> Export Report
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 bg-[#f9fafc]">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-slate-800">Ringkasan Eksekutif</h2>
            <p className="text-slate-500 text-sm">Update terakhir: {new Date().toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' })}</p>
          </div>
          <div className="flex gap-3">
             <div className="bg-white px-4 py-2 rounded-lg border border-gray-200 flex items-center gap-2 text-sm font-medium shadow-sm">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                Sistem Online
             </div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          <KPICard title="Total Pedagang" value={dashboardStats.total} icon={<Users className="text-blue-600" />} color="blue" />
          <KPICard title="Total Valid" value={dashboardStats.valid} icon={<CheckCircle className="text-green-600" />} color="green" />
          <KPICard title="Tidak Valid" value={dashboardStats.invalid} icon={<XCircle className="text-red-600" />} color="red" />
          <KPICard title="Wilayah Aktif" value={dashboardStats.locations} icon={<MapPin className="text-orange-600" />} color="orange" />
          <KPICard title="% Validitas" value={`${dashboardStats.validityPct}%`} icon={<TrendingUp className="text-purple-600" />} color="purple" trend={dashboardStats.validityPct} />
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <ChartContainer title="Sebaran Pedagang per Lokasi" subtitle="Jumlah pedagang berdasarkan area terdaftar">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData_SebaranLokasi} layout="vertical" margin={{ left: 40, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f1f1f1" />
                <XAxis type="number" hide />
                <YAxis dataKey="lokasi" type="category" width={100} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                <Bar dataKey="jumlah" fill="#0078D4" radius={[0, 4, 4, 0]} barSize={20} />
              </BarChart>
            </ResponsiveContainer>
          </ChartContainer>

          <ChartContainer title="Distribusi Kategori Produk" subtitle="Pecahan pedagang berdasarkan jenis dagangan">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={chartData_SebaranKategori}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="jumlah"
                  nameKey="kategori"
                >
                  {chartData_SebaranKategori.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend layout="vertical" align="right" verticalAlign="middle" iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <ChartContainer title="Analisis Validitas Per Wilayah" subtitle="Perbandingan data valid dan tidak valid per area">
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={chartData_SebaranLokasi.slice(0, 5)}>
                  <defs>
                    <linearGradient id="colorValid" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0078D4" stopOpacity={0.2}/>
                      <stop offset="95%" stopColor="#0078D4" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f1f1" />
                  <XAxis dataKey="lokasi" axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Area type="monotone" dataKey="jumlah" stroke="#0078D4" fillOpacity={1} fill="url(#colorValid)" strokeWidth={3} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartContainer>
          </div>

          <ChartContainer title="Alasan Tidak Valid" subtitle="Faktor utama kegagalan verifikasi">
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData_AlasanTidakValid}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f1f1" />
                <XAxis dataKey="alasan" hide />
                <YAxis hide />
                <Tooltip contentStyle={{ fontSize: '12px' }} />
                <Bar dataKey="jumlah" fill="#D83B01" radius={[4, 4, 0, 0]}>
                  {chartData_AlasanTidakValid.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={index === 0 ? '#A4262C' : '#D83B01'} opacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-4 space-y-2">
              {chartData_AlasanTidakValid.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">{item.alasan}</span>
                  <span className="font-bold text-slate-800">{item.jumlah}</span>
                </div>
              ))}
            </div>
          </ChartContainer>
        </div>
      </main>
    </div>
  );
};

interface KPICardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'red' | 'orange' | 'purple';
  trend?: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, icon, color, trend }) => {
  const colorMap = {
    blue: 'border-blue-500',
    green: 'border-green-500',
    red: 'border-red-500',
    orange: 'border-orange-500',
    purple: 'border-purple-500'
  };

  return (
    <div className={`bg-white p-6 rounded-xl shadow-sm border-l-4 ${colorMap[color]} hover:shadow-md transition-shadow`}>
      <div className="flex justify-between items-start mb-2">
        <div className="p-2 bg-gray-50 rounded-lg">
          {icon}
        </div>
        {trend && (
          <span className={`text-xs font-bold ${parseFloat(trend) > 80 ? 'text-green-600' : 'text-orange-500'}`}>
            {parseFloat(trend) > 80 ? 'HIGH' : 'LOW'}
          </span>
        )}
      </div>
      <div>
        <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{title}</p>
        <h4 className="text-2xl font-black text-slate-800">{value}</h4>
      </div>
    </div>
  );
};

const ChartContainer: React.FC<{ title: string, subtitle: string, children: React.ReactNode }> = ({ title, subtitle, children }) => {
  return (
    <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col h-full">
      <div className="mb-6">
        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
          {title}
        </h3>
        <p className="text-slate-400 text-xs font-medium">{subtitle}</p>
      </div>
      <div className="flex-1 min-h-[250px]">
        {children}
      </div>
    </div>
  );
};

export default App;
