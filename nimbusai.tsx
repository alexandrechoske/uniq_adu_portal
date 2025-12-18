import React from 'react';
import { 
  LayoutDashboard, 
  Bot, 
  Inbox, 
  Workflow, 
  Calendar, 
  Database, 
  Users, 
  Briefcase, 
  Plug, 
  Settings,
  Search,
  HelpCircle,
  Bell,
  ChevronDown,
  Wand2,
  FolderOpen,
  Sun,
  Moon
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart, 
  Pie, 
  Cell
} from 'recharts';
import { LeadData } from '../types';

const leadData: LeadData[] = [
  { month: 'Dec', won: 4500, lost: 2000 },
  { month: 'Jan', won: 4800, lost: 2500 },
  { month: 'Feb', won: 5200, lost: 3000 },
  { month: 'Mar', won: 7500, lost: 2000 }, // Peak won
  { month: 'Apr', won: 5800, lost: 4000 },
  { month: 'May', won: 4800, lost: 5000 },
];

const sourceData = [
  { name: 'LinkedIn', value: 35, color: '#1E40AF' }, // Dark Blue
  { name: 'Dribbble', value: 25, color: '#3B82F6' }, // Blue
  { name: 'Clutch', value: 15, color: '#93C5FD' },  // Light Blue
  { name: 'Others', value: 25, color: '#E5E7EB' },  // Gray
];

const sourceDataDark = [
  { name: 'LinkedIn', value: 35, color: '#3B82F6' }, 
  { name: 'Dribbble', value: 25, color: '#60A5FA' }, 
  { name: 'Clutch', value: 15, color: '#93C5FD' }, 
  { name: 'Others', value: 25, color: '#374151' }, 
];

interface SaasDashboardProps {
  darkMode: boolean;
  toggleTheme: () => void;
}

const SaasDashboard: React.FC<SaasDashboardProps> = ({ darkMode, toggleTheme }) => {
  const bgColor = darkMode ? 'bg-nimbus-dark' : 'bg-[#F3F4F6]';
  const textColor = darkMode ? 'text-white' : 'text-slate-800';
  const cardBg = darkMode ? 'bg-nimbus-card border-white/5' : 'bg-white border-gray-100';
  const subText = darkMode ? 'text-gray-400' : 'text-gray-500';
  
  // Chart colors based on theme
  const chartGridStroke = darkMode ? '#374151' : '#f0f0f0';
  const chartAxisStroke = darkMode ? '#9CA3AF' : '#9CA3AF';
  const tooltipBg = darkMode ? '#1F2937' : '#fff';
  const tooltipColor = darkMode ? '#F3F4F6' : '#000';

  return (
    <div className={`flex h-screen ${bgColor} ${textColor} font-sans overflow-hidden transition-colors duration-300`}>
      {/* Sidebar */}
      <aside className={`w-64 flex flex-col flex-shrink-0 transition-colors duration-300 ${
        darkMode 
          ? 'bg-[#050505] border-r border-white/5' 
          : 'bg-gradient-to-b from-[#0F172A] to-[#1E3A8A] text-white'
      }`}>
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center">
            <div className="w-4 h-4 rounded-full bg-blue-400 animate-pulse"></div>
          </div>
          <span className="text-lg font-semibold tracking-tight">Nimbus ai</span>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-8">
          <div className="space-y-1">
            <SidebarItem darkMode={darkMode} icon={<LayoutDashboard size={18} />} label="Dashboard" active />
            <SidebarItem darkMode={darkMode} icon={<Bot size={18} />} label="Agents" />
            <SidebarItem darkMode={darkMode} icon={<Inbox size={18} />} label="Inbox" badge="2" />
            <SidebarItem darkMode={darkMode} icon={<Workflow size={18} />} label="Workflows" hasSub />
            <SidebarItem darkMode={darkMode} icon={<Calendar size={18} />} label="Calendar" />
          </div>

          <div>
            <p className={`px-3 text-xs font-semibold mb-2 uppercase tracking-wider ${darkMode ? 'text-gray-500' : 'text-blue-200/50'}`}>Database</p>
            <div className="space-y-1">
              <SidebarItem darkMode={darkMode} icon={<Database size={18} />} label="Insights" />
              <SidebarItem darkMode={darkMode} icon={<Users size={18} />} label="Contacts" />
              <SidebarItem darkMode={darkMode} icon={<Briefcase size={18} />} label="Companies" />
            </div>
          </div>

          <div>
            <p className={`px-3 text-xs font-semibold mb-2 uppercase tracking-wider ${darkMode ? 'text-gray-500' : 'text-blue-200/50'}`}>Mics</p>
            <div className="space-y-1">
              <SidebarItem darkMode={darkMode} icon={<Plug size={18} />} label="Integrations" />
              <SidebarItem darkMode={darkMode} icon={<Settings size={18} />} label="Settings" />
            </div>
          </div>
        </div>

        {/* Upgrade Card */}
        <div className="p-4">
          <div className={`backdrop-blur-sm rounded-xl p-4 relative overflow-hidden ${darkMode ? 'bg-white/5 border border-white/5' : 'bg-white/10'}`}>
            <div className={`absolute -top-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-40 ${darkMode ? 'bg-purple-500' : 'bg-blue-500'}`}></div>
            <div className="flex justify-between items-start mb-2 relative z-10">
              <h4 className="font-semibold text-sm">Upgrade to Premium</h4>
              <button className="text-white/50 hover:text-white"><span className="text-lg">×</span></button>
            </div>
            <p className={`text-xs mb-3 leading-relaxed relative z-10 ${darkMode ? 'text-gray-400' : 'text-blue-100'}`}>
              Unlock advanced AI features and unlimited workflows.
            </p>
            <button className={`text-xs font-semibold px-3 py-1.5 rounded-lg shadow-sm transition-colors relative z-10 ${
              darkMode ? 'bg-white text-black hover:bg-gray-200' : 'bg-white text-blue-900 hover:bg-blue-50'
            }`}>
              Upgrade
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header */}
        <header className={`h-16 flex items-center justify-between px-8 flex-shrink-0 border-b transition-colors duration-300 ${
          darkMode ? 'bg-nimbus-dark border-white/5' : 'bg-white border-gray-100'
        }`}>
          <div className={`flex items-center rounded-lg px-3 py-2 w-96 border transition-all ${
            darkMode 
              ? 'bg-[#11141C] border-white/5 focus-within:border-gray-600' 
              : 'bg-gray-50 border-transparent focus-within:border-blue-300 focus-within:bg-white'
          }`}>
            <Search size={16} className={`${darkMode ? 'text-gray-500' : 'text-gray-400'} mr-2`} />
            <input 
              type="text" 
              placeholder="Search lead, contact, and more..." 
              className="bg-transparent border-none outline-none text-sm w-full placeholder-gray-500"
            />
            <div className={`flex gap-1 ${darkMode ? 'text-gray-600' : 'text-gray-400'}`}>
              <span className={`border rounded px-1.5 py-0.5 text-[10px] ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>⌘</span>
              <span className={`border rounded px-1.5 py-0.5 text-[10px] ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>F</span>
            </div>
          </div>

          <div className={`flex items-center gap-6 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            <button onClick={toggleTheme} className="hover:text-gray-800 dark:hover:text-white transition-colors">
              {darkMode ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <HelpCircle size={20} className="hover:text-gray-800 dark:hover:text-white cursor-pointer" />
            <div className="relative hover:text-gray-800 dark:hover:text-white cursor-pointer">
              <Bell size={20} />
              <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full border-2 border-white dark:border-nimbus-dark"></span>
            </div>
            <div className={`flex items-center gap-2 cursor-pointer p-1.5 rounded-lg transition-colors ${
              darkMode ? 'hover:bg-white/5' : 'hover:bg-gray-50'
            }`}>
              <img src="https://picsum.photos/100/100?random=88" alt="Profile" className="w-8 h-8 rounded-full" />
              <span className={`text-sm font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>Jimmy H.</span>
              <ChevronDown size={14} />
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-8 dark-scroll">
          <h1 className={`text-2xl font-bold mb-6 ${darkMode ? 'text-white' : 'text-gray-900'}`}>Dashboard</h1>

          {/* Hero / Action Section */}
          <div className={`rounded-2xl p-8 mb-6 shadow-sm border flex flex-col items-center justify-center text-center transition-colors ${cardBg}`}>
            <h2 className={`text-lg font-semibold mb-6 ${darkMode ? 'text-white' : 'text-gray-900'}`}>What will you build?</h2>
            <div className="flex gap-12">
              <ActionButton darkMode={darkMode} icon={<Workflow size={24} />} label="Workflows" />
              <ActionButton darkMode={darkMode} icon={<Wand2 size={24} />} label="AI Toolkits" />
              <ActionButton darkMode={darkMode} icon={<FolderOpen size={24} />} label="My Files" />
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <StatCard darkMode={darkMode} label="Completed Calls" value="10210" trend="36%" trendUp={true} />
            <StatCard darkMode={darkMode} label="Total Contacts" value="3210" trend="10%" trendUp={true} />
            <StatCard darkMode={darkMode} label="Active Company" value="3210" trend="24%" trendUp={true} />
            <StatCard darkMode={darkMode} label="Active Workflow" value="26" trend="6%" trendUp={true} />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            {/* Active Workflows List */}
            <div className={`p-6 rounded-2xl shadow-sm border col-span-1 ${cardBg}`}>
              <div className="flex justify-between items-center mb-6">
                <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Active Workflows</h3>
              </div>
              <div className="space-y-6">
                {[
                  { title: 'Pixel to Profit: The Growth UX Advantage', time: '02:00 pm Jun 2, 2025' },
                  { title: 'VentureScale: Design for High-Growth Portfolios', time: '02:00 pm Jun 15, 2025' },
                  { title: 'Startup Signal', time: '11:00 am Jul 8, 2025' },
                  { title: 'AI Meets Sales', time: '11:00-12:00 Aug 1, 2025' }
                ].map((item, i) => (
                  <div key={i} className="flex justify-between items-start group cursor-pointer">
                    <div>
                      <h4 className={`text-sm font-medium transition-colors ${
                        darkMode ? 'text-gray-300 group-hover:text-blue-400' : 'text-gray-800 group-hover:text-blue-600'
                      }`}>{item.title}</h4>
                      <p className={`text-xs mt-1 flex items-center gap-1 ${subText}`}>
                         <span className={`w-1.5 h-1.5 rounded-full ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`}></span> {item.time}
                      </p>
                    </div>
                    <span className={`${darkMode ? 'text-gray-600' : 'text-gray-300'} group-hover:text-blue-500 transition-colors`}>›</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Leads Chart */}
            <div className={`p-6 rounded-2xl shadow-sm border col-span-1 lg:col-span-2 ${cardBg}`}>
              <div className="flex justify-between items-start mb-6">
                <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Leads</h3>
                <div className="flex gap-2">
                  <TimeFilterButton darkMode={darkMode} label="6 months" active />
                  <TimeFilterButton darkMode={darkMode} label="30 days" />
                  <TimeFilterButton darkMode={darkMode} label="7 days" />
                </div>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={leadData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartGridStroke} />
                    <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{fill: chartAxisStroke, fontSize: 12}} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{fill: chartAxisStroke, fontSize: 12}} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: tooltipBg, borderRadius: '8px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', border: 'none', color: tooltipColor }}
                      itemStyle={{ fontSize: '12px' }}
                    />
                    <Line type="monotone" dataKey="won" stroke="#10B981" strokeWidth={2} dot={{r: 4, fill: '#10B981', strokeWidth: 2, stroke: darkMode ? '#111' : '#fff'}} activeDot={{ r: 6 }} name="Closed won" />
                    <Line type="monotone" dataKey="lost" stroke="#EF4444" strokeWidth={2} dot={{r: 4, fill: '#EF4444', strokeWidth: 2, stroke: darkMode ? '#111' : '#fff'}} name="Closed lost" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-6 mt-2">
                 <div className={`flex items-center gap-2 text-xs ${subText}`}>
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Closed won
                 </div>
                 <div className={`flex items-center gap-2 text-xs ${subText}`}>
                    <span className="w-2 h-2 rounded-full bg-red-500"></span> Closed lost
                 </div>
              </div>
            </div>
          </div>

          {/* Bottom Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Funnel Count */}
            <div className={`p-6 rounded-2xl shadow-sm border ${cardBg}`}>
                <div className="flex justify-between items-center mb-6">
                    <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Funnel count</h3>
                    <div className="text-right">
                        <span className={`text-2xl font-bold block ${darkMode ? 'text-white' : 'text-gray-900'}`}>2402</span>
                        <span className="text-xs text-green-500 font-medium">↑ 12% active leads</span>
                    </div>
                </div>
                <div className={`w-full rounded-full h-3 flex overflow-hidden mb-6 ${darkMode ? 'bg-gray-800' : 'bg-gray-100'}`}>
                    <div className="bg-[#1E3A8A] w-[45%]"></div>
                    <div className="bg-[#3B82F6] w-[35%]"></div>
                    <div className="bg-[#60A5FA] w-[10%]"></div>
                    <div className="bg-[#BFDBFE] w-[10%]"></div>
                </div>
                <div className="space-y-3">
                    <div className="flex justify-between text-sm">
                        <div className="flex items-center gap-2">
                             <span className="w-2 h-2 rounded-full bg-[#1E3A8A]"></span> 
                             <span className={subText}>Closed won</span>
                        </div>
                        <span className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>10210</span>
                        <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>2 days</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <div className="flex items-center gap-2">
                             <span className="w-2 h-2 rounded-full bg-[#3B82F6]"></span> 
                             <span className={subText}>Negotiations</span>
                        </div>
                        <span className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>3240</span>
                        <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>2 days</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <div className="flex items-center gap-2">
                             <span className="w-2 h-2 rounded-full bg-[#60A5FA]"></span> 
                             <span className={subText}>In conversation</span>
                        </div>
                        <span className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>1841</span>
                        <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>2 days</span>
                    </div>
                </div>
            </div>

            {/* Sources */}
            <div className={`p-6 rounded-2xl shadow-sm border flex flex-col md:flex-row gap-6 items-center ${cardBg}`}>
                <div className="flex-1 w-full">
                   <div className="flex justify-between items-center mb-4">
                     <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>Sources</h3>
                     <div className="flex gap-1">
                        <span className={`text-xs px-2 py-1 border rounded ${darkMode ? 'bg-white/10 border-white/10 text-gray-300' : 'bg-gray-50 text-gray-600'}`}>Leads came</span>
                        <span className={`text-xs px-2 py-1 border rounded ${darkMode ? 'bg-transparent border-white/10 text-gray-500' : 'bg-white text-gray-400'}`}>Leads converted</span>
                     </div>
                   </div>
                   <div className="h-48 relative">
                       <ResponsiveContainer width="100%" height="100%">
                           <PieChart>
                               <Pie
                                data={darkMode ? sourceDataDark : sourceData}
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={2}
                                dataKey="value"
                                startAngle={90}
                                endAngle={-270}
                                stroke="none"
                               >
                                {(darkMode ? sourceDataDark : sourceData).map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                               </Pie>
                           </PieChart>
                       </ResponsiveContainer>
                       <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                           <span className={`text-xs font-medium ${subText}`}>Total</span>
                       </div>
                   </div>
                </div>
                <div className="w-full md:w-48 flex-shrink-0">
                    <h4 className={`text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-800'}`}>Top 5 sources</h4>
                    <div className="space-y-3">
                        {(darkMode ? sourceDataDark : sourceData).map((source, i) => (
                            <div key={i} className="flex justify-between items-center text-sm">
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full" style={{backgroundColor: source.color}}></span>
                                    <span className={subText}>{source.name}</span>
                                </div>
                                <span className={`font-semibold ${darkMode ? 'text-gray-200' : 'text-gray-900'}`}>{source.value}%</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// Components
const SidebarItem = ({ icon, label, active = false, badge, hasSub = false, darkMode }: { icon: React.ReactNode, label: string, active?: boolean, badge?: string, hasSub?: boolean, darkMode: boolean }) => {
  let containerClass = "text-blue-100 hover:bg-white/10 hover:text-white";
  
  if (darkMode) {
    if (active) containerClass = "bg-white/10 text-white";
    else containerClass = "text-gray-400 hover:text-white hover:bg-white/5";
  } else {
    if (active) containerClass = "bg-blue-600 text-white shadow-lg shadow-blue-900/20";
    else containerClass = "text-blue-100 hover:bg-white/10 hover:text-white";
  }

  return (
    <div className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors group ${containerClass}`}>
      <div className="flex items-center gap-3">
        {icon}
        <span className="text-sm font-medium">{label}</span>
      </div>
      {badge && <span className={`text-xs px-1.5 py-0.5 rounded text-white ${darkMode ? 'bg-blue-600' : 'bg-blue-500'}`}>{badge}</span>}
      {hasSub && <span className="text-xs opacity-50 group-hover:opacity-100">›</span>}
    </div>
  );
};

const ActionButton = ({ icon, label, darkMode }: { icon: React.ReactNode, label: string, darkMode: boolean }) => (
  <button className="flex flex-col items-center gap-3 group">
    <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
      darkMode 
        ? 'bg-white/5 text-gray-400 group-hover:bg-blue-500/20 group-hover:text-blue-400' 
        : 'bg-gray-50 text-gray-500 group-hover:bg-blue-50 group-hover:text-blue-600'
    }`}>
      {icon}
    </div>
    <span className={`text-xs font-medium ${darkMode ? 'text-gray-400 group-hover:text-white' : 'text-gray-600 group-hover:text-gray-900'}`}>{label}</span>
  </button>
);

const StatCard = ({ label, value, trend, trendUp, darkMode }: { label: string, value: string, trend: string, trendUp: boolean, darkMode: boolean }) => (
  <div className={`p-6 rounded-2xl shadow-sm border ${darkMode ? 'bg-nimbus-card border-white/5' : 'bg-white border-gray-100'}`}>
    <h3 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{label}</h3>
    <div className="flex items-end gap-3">
      <span className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>{value}</span>
      <span className={`text-xs font-medium mb-1 ${trendUp ? 'text-green-500' : 'text-red-500'}`}>
        {trendUp ? '↑' : '↓'} {trend} vs last month
      </span>
    </div>
  </div>
);

const TimeFilterButton = ({ label, active = false, darkMode }: { label: string, active?: boolean, darkMode: boolean }) => {
  if (darkMode) {
    return (
      <button className={`px-3 py-1 text-xs font-medium rounded-md border transition-colors ${
        active 
          ? 'bg-white/10 text-white border-white/10' 
          : 'bg-transparent text-gray-500 border-white/5 hover:bg-white/5 hover:text-gray-300'
      }`}>
        {label}
      </button>
    );
  }
  return (
    <button className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
      active 
        ? 'bg-gray-100 text-gray-600' 
        : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
    }`}>
      {label}
    </button>
  );
}

export default SaasDashboard;