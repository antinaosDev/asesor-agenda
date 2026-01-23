import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  Activity,
  CheckCircle,
  FileText,
  TrendingUp,
  Clipboard,
  Menu
} from 'lucide-react';

// --- DATA MOCKUP BASED ON UPLOADED CSV SNIPPETS FOR CHOLCHOL ---
// ACTUALIZADO: Se eliminó Meta 11 (Influenza) a petición del usuario

const iaapsData = [
  { id: '1', name: 'Autoevaluación MAIS', logrado: 100, meta: 100, cumplimiento: 100, category: 'Gestión' },
  { id: '2.1', name: 'Funcionamiento 8-20hrs', logrado: 100, meta: 100, cumplimiento: 100, category: 'Acceso' },
  { id: '2.2', name: 'Fármacos Trazadores', logrado: 100, meta: 100, cumplimiento: 100, category: 'Acceso' },
  { id: '3', name: 'Tasa Consultas Morbilidad', logrado: 79.0, meta: 89.0, cumplimiento: 88.8, category: 'Producción' },
  { id: '4', name: 'Derivación Nivel Secundario', logrado: 7.61, meta: 9.5, cumplimiento: 100, category: 'Gestión' }, // Menor es mejor
  { id: '5', name: 'Visita Domiciliaria Integral', logrado: 25.0, meta: 21.0, cumplimiento: 100, category: 'Producción' },
  { id: '6.1A', name: 'EMP Mujeres 20-64', logrado: 27.0, meta: 27.0, cumplimiento: 99.7, category: 'Preventivo' },
  { id: '6.1B', name: 'EMP Hombres 20-64', logrado: 22.9, meta: 23.6, cumplimiento: 96.9, category: 'Preventivo' },
  { id: '6.2', name: 'EMP Adulto Mayor >65', logrado: 44.1, meta: 48.6, cumplimiento: 90.7, category: 'Preventivo' },
  { id: '7', name: 'Desarrollo Psicomotor 12-23m', logrado: 102.4, meta: 92.0, cumplimiento: 100, category: 'Infantil' },
  { id: '8', name: 'Salud Integral Adolescente', logrado: 21.5, meta: 21.5, cumplimiento: 100, category: 'Adolescente' },
  { id: '9.1', name: 'Cobertura Salud Mental', logrado: 18.2, meta: 18.2, cumplimiento: 100, category: 'Salud Mental' },
  { id: '9.2', name: 'Controles Salud Mental', logrado: 4.97, meta: 4.9, cumplimiento: 100, category: 'Salud Mental' },
  { id: '9.3', name: 'Alta Clínica Salud Mental', logrado: 22.3, meta: 7.0, cumplimiento: 100, category: 'Salud Mental' },
  { id: '10', name: 'Cumplimiento GES', logrado: 100, meta: 100, cumplimiento: 100, category: 'Gestión' },
  { id: '12', name: 'Ingreso Precoz Embarazo', logrado: 89.9, meta: 86.0, cumplimiento: 100, category: 'Mujer' },
  { id: '13', name: 'Regulación Fertilidad Adoles.', logrado: 21.5, meta: 22.0, cumplimiento: 97.5, category: 'Mujer' },
  { id: '14', name: 'Cobertura DM2', logrado: 72.2, meta: 76.2, cumplimiento: 94.7, category: 'Crónicos' },
  { id: '15', name: 'Cobertura HTA', logrado: 52.7, meta: 60.0, cumplimiento: 87.9, category: 'Crónicos' },
  { id: '16', name: 'Salud Bucal < 3 años', logrado: 67.9, meta: 62.0, cumplimiento: 100, category: 'Infantil' },
  { id: '17', name: 'Nutricional Normal < 2 años', logrado: 50.3, meta: 59.8, cumplimiento: 84.2, category: 'Infantil' },
];

const metasSanitariasData = [
  { id: 'M1', name: 'Recup. Desarrollo Psicomotor', logrado: 100, meta: 90, cumplimiento: 100, description: 'Niños 12-23 meses recuperados' },
  { id: 'M2', name: 'Pap Vigente 25-64 años', logrado: 71.1, meta: 72.1, cumplimiento: 98.55, description: 'Cobertura PAP mujeres' },
  { id: 'M3a', name: 'Control Odontológico 0-9', logrado: 36.3, meta: 36, cumplimiento: 100, description: 'Cobertura odontológica infantil' },
  { id: 'M3b', name: 'Libres de Caries 6 años', logrado: 21.1, meta: 18, cumplimiento: 100, description: 'Salud bucal preescolar' },
  { id: 'M4a', name: 'Evaluación DM2 < 7%', logrado: 28.3, meta: 26.8, cumplimiento: 100, description: 'Compensación DM2' },
  { id: 'M4b', name: 'Evaluación Pie Diabético', logrado: 83.6, meta: 90, cumplimiento: 92.93, description: 'Prevención pie diabético' },
  { id: 'M5', name: 'Cobertura Efectiva HTA', logrado: 36.7, meta: 39.5, cumplimiento: 93.02, description: 'Compensación HTA' },
  { id: 'M6', name: 'Lactancia Materna 6to mes', logrado: 68.3, meta: 72, cumplimiento: 94.9, description: 'LME exclusiva' },
  { id: 'M7', name: 'Cobertura Asma/EPOC', logrado: 12.1, meta: 12, cumplimiento: 100, description: 'Salud Respiratoria' },
  { id: 'M8', name: 'Gestión Comunitaria', logrado: 100, meta: 100, cumplimiento: 100, description: 'Participación social' },
];

// --- COMPONENTS ---

const Card = ({ title, value, subtext, subtext2, icon: Icon, colorClass }) => (
  <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-600 hover:shadow-xl transition-all duration-300">
    <div className="flex justify-between items-start">
      <div>
        <p className="text-sm font-medium text-gray-500 uppercase tracking-wider">{title}</p>
        <h3 className="text-3xl font-bold text-gray-800 mt-2">{value}</h3>
        <p className={`text-xs mt-2 font-semibold ${colorClass}`}>{subtext}</p>
        {subtext2 && <p className="text-xs mt-1 font-semibold text-gray-500">{subtext2}</p>}
      </div>
      <div className={`p-3 rounded-full ${colorClass} bg-opacity-20`}>
        <Icon className={`w-6 h-6 ${colorClass.replace('text-', 'text-opacity-100 ')}`} />
      </div>
    </div>
  </div>
);

const ProgressBar = ({ label, percentage, color = "bg-blue-600" }) => (
  <div className="mb-4">
    <div className="flex justify-between mb-1">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <span className="text-sm font-bold text-gray-700">{percentage}%</span>
    </div>
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div
        className={`h-2.5 rounded-full transition-all duration-1000 ${percentage >= 90 ? 'bg-blue-600' : 'bg-yellow-400'}`}
        style={{ width: `${Math.min(percentage, 100)}%` }}
      ></div>
    </div>
  </div>
);

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const dataItem = payload[0].payload;
    return (
      <div className="bg-blue-900 text-white p-3 rounded-lg shadow-lg border border-blue-700">
        <p className="font-bold border-b border-blue-500 pb-1 mb-2">ID: {dataItem.id} - {label}</p>
        <p className="text-sm mb-1 text-cyan-200">
          <span className="font-semibold">Logrado: </span>{dataItem.logrado}%
        </p>
        <p className="text-sm mb-1 text-yellow-300">
          <span className="font-semibold">Meta: </span>{dataItem.meta}%
        </p>
        <div className="mt-2 pt-2 border-t border-blue-800">
          <p className="text-sm font-bold text-white">
            Cumplimiento: {dataItem.cumplimiento}%
          </p>
        </div>
      </div>
    );
  }
  return null;
};

const IndicatorRow = ({ item }) => {
  const isSuccess = item.cumplimiento >= 90;
  return (
    <tr className="hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-0">
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${isSuccess ? 'bg-blue-100 text-blue-600' : 'bg-yellow-100 text-yellow-600'}`}>
            <span className="font-bold text-xs">{item.id}</span>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900">{item.name}</div>
            <div className="text-xs text-gray-500">{item.category}</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center">
        <span className="text-sm font-bold text-blue-700">{item.logrado}%</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-center">
        <span className="text-sm text-gray-600">{item.meta}%</span>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="w-full bg-gray-200 rounded-full h-2 mr-2">
            <div
              className={`h-2 rounded-full ${item.cumplimiento >= 90 ? 'bg-blue-800' : 'bg-yellow-400'}`}
              style={{ width: `${Math.min(item.cumplimiento, 100)}%` }}
            />
          </div>
          <span className={`text-sm font-bold ${item.cumplimiento >= 90 ? 'text-blue-800' : 'text-yellow-600'}`}>
            {item.cumplimiento}%
          </span>
        </div>
      </td>
    </tr>
  );
};

// --- MAIN APP COMPONENT ---

export default function CesfamCholcholReport() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ACTUALIZADO: Valores de KPI fijos según planilla proporcionada por el usuario
  const iaapsScore = 96.75;
  const metasScoreFull = 97.43;
  const metasScoreBase = 91.18;

  const getActiveTabClass = (tabName) =>
    `px-4 py-2 font-medium text-sm rounded-t-lg transition-colors duration-200 ${activeTab === tabName
      ? 'bg-white text-blue-800 border-t-4 border-yellow-400 shadow-sm'
      : 'text-blue-100 hover:bg-blue-800 hover:text-white'
    }`;

  const renderDashboard = () => (
    <div className="space-y-6 animate-fade-in">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card
          title="Cumplimiento Global IAAPS"
          value={`${iaapsScore}%`}
          subtext="Según Planilla Oficial"
          icon={Activity}
          colorClass="text-blue-600"
        />
        <Card
          title="Ley 19.813"
          value={`${metasScoreFull}%`}
          subtext="Con Meta 8 Cumplida (100%)"
          subtext2={`Sin Meta 8: ${metasScoreBase}%`}
          icon={CheckCircle}
          colorClass="text-yellow-500"
        />
        <Card
          title="Total Evaluados"
          value={iaapsData.length + metasSanitariasData.length}
          subtext="Indicadores totales procesados"
          icon={FileText}
          colorClass="text-cyan-500"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart IAAPS Full */}
        <div className="bg-white p-6 rounded-xl shadow-lg">
          <h3 className="text-lg font-bold text-blue-900 mb-4 flex items-center">
            <TrendingUp className="w-5 h-5 mr-2 text-yellow-500" />
            Rendimiento IAAPS (Logrado vs Meta)
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Comparativa de los 21 indicadores (excluyendo Influenza). Desplácese horizontalmente para ver todos los detalles.
          </p>
          <div className="h-96 w-full overflow-x-auto">
            <div className="min-w-[800px] h-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={iaapsData} margin={{ top: 20, right: 30, left: 0, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis
                    dataKey="id"
                    stroke="#6b7280"
                    interval={0}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis stroke="#6b7280" label={{ value: '%', angle: -90, position: 'insideLeft' }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend verticalAlign="top" wrapperStyle={{ paddingBottom: '20px' }} />
                  <Bar dataKey="logrado" name="% Valor Logrado" fill="#2563eb" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="meta" name="% Meta Anual" fill="#facc15" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Resumen Metas Sanitarias */}
        <div className="bg-white p-6 rounded-xl shadow-lg">
          <h3 className="text-lg font-bold text-blue-900 mb-4 flex items-center">
            <Clipboard className="w-5 h-5 mr-2 text-yellow-500" />
            Estado Metas Sanitarias 19.813
          </h3>
          <div className="space-y-4 overflow-y-auto max-h-96 pr-2">
            {metasSanitariasData.map((meta) => (
              <ProgressBar
                key={meta.id}
                label={`${meta.id} - ${meta.name}`}
                percentage={meta.cumplimiento}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  const renderIaapsDetails = () => (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden animate-fade-in">
      <div className="p-6 border-b border-gray-100 bg-blue-50">
        <h3 className="text-xl font-bold text-blue-900">Detalle de Indicadores IAAPS</h3>
        <p className="text-sm text-blue-600 mt-1">Desglose completo de indicadores de actividad de APS para Cholchol</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-blue-900 text-white">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Indicador</th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider">Logrado</th>
              <th className="px-6 py-3 text-center text-xs font-medium uppercase tracking-wider">Meta Corte</th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider">Estado Cumplimiento</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {iaapsData.map((item) => (
              <IndicatorRow key={item.id} item={item} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderMetasDetails = () => (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden animate-fade-in">
      <div className="p-6 border-b border-gray-100 bg-blue-50">
        <h3 className="text-xl font-bold text-blue-900">Detalle Metas Sanitarias (Ley 19.813)</h3>
        <p className="text-sm text-blue-600 mt-1">Evaluación de cumplimiento para asignación de desarrollo y desempeño colectivo</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6">
        {metasSanitariasData.map((meta) => {
          const isCumplido = meta.cumplimiento >= 90;
          return (
            <div key={meta.id} className="border border-gray-200 rounded-lg p-4 hover:border-blue-400 transition-colors bg-white shadow-sm">
              <div className="flex justify-between items-center mb-2">
                <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">{meta.id}</span>
                <span className={`text-xs font-bold px-2 py-1 rounded ${isCumplido ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                  {isCumplido ? 'Cumplido' : 'En Progreso'}
                </span>
              </div>
              <h4 className="font-bold text-gray-800 mb-1">{meta.name}</h4>
              <p className="text-xs text-gray-500 mb-3">{meta.description}</p>

              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Logrado: <strong>{meta.logrado}%</strong></span>
                <span>Meta: <strong>{meta.meta}%</strong></span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${isCumplido ? 'bg-green-500' : 'bg-yellow-400'}`}
                  style={{ width: `${Math.min(meta.cumplimiento, 100)}%` }}
                ></div>
              </div>
              <div className="text-right mt-1">
                <span className={`text-xs font-bold ${isCumplido ? 'text-green-700' : 'text-blue-900'}`}>{meta.cumplimiento}% Cumplimiento</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100 font-sans">
      {/* Top Navigation Bar */}
      <nav className="bg-blue-900 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center">
              <div className="flex-shrink-0 bg-white p-2 rounded-full">
                <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                  C
                </div>
              </div>
              <div className="ml-4">
                <h1 className="text-white text-xl font-bold tracking-tight">CESFAM CHOLCHOL</h1>
                <p className="text-blue-200 text-xs">Informe de Gestión y Resultados - Corte N°4 2025</p>
              </div>
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <span className="text-yellow-400 text-sm font-semibold bg-blue-800 px-3 py-1 rounded-full">
                  Enero - Diciembre 2025
                </span>
              </div>
            </div>
            <div className="-mr-2 flex md:hidden">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-white hover:text-yellow-400 p-2">
                <Menu />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-2">
          <div className="flex space-x-2">
            <button onClick={() => setActiveTab('dashboard')} className={getActiveTabClass('dashboard')}>
              Panel General
            </button>
            <button onClick={() => setActiveTab('iaaps')} className={getActiveTabClass('iaaps')}>
              Detalle IAAPS
            </button>
            <button onClick={() => setActiveTab('metas')} className={getActiveTabClass('metas')}>
              Metas Sanitarias (19.813)
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'iaaps' && renderIaapsDetails()}
        {activeTab === 'metas' && renderMetasDetails()}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <p className="text-sm text-gray-500">© 2025 CESFAM Cholchol. Departamento de Salud Municipal.</p>
          <div className="flex space-x-2">
            <div className="w-3 h-3 rounded-full bg-blue-900"></div>
            <div className="w-3 h-3 rounded-full bg-blue-600"></div>
            <div className="w-3 h-3 rounded-full bg-cyan-400"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
          </div>
        </div>
      </footer>
    </div>
  );
}
