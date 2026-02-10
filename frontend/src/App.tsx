import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Registry from './pages/Registry'
import FeatureDetail from './pages/FeatureDetail'
import OptionDetail from './pages/OptionDetail'
import SettingDetail from './pages/SettingDetail'
import Releases from './pages/Releases'
import ReleaseDetail from './pages/ReleaseDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="registry" element={<Registry />} />
        <Route path="features/:featureId" element={<FeatureDetail />} />
        <Route path="options/:optionId" element={<OptionDetail />} />
        <Route path="settings/:settingId" element={<SettingDetail />} />
        <Route path="releases" element={<Releases />} />
        <Route path="releases/:contentId" element={<ReleaseDetail />} />
        {/* Redirects from old routes */}
        <Route path="features" element={<Navigate to="/registry" replace />} />
        <Route path="options" element={<Navigate to="/registry" replace />} />
      </Route>
    </Routes>
  )
}

export default App
