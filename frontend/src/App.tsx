import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Registry from './pages/Registry'
import FeatureDetail from './pages/FeatureDetail'
import OptionDetail from './pages/OptionDetail'
import SettingDetail from './pages/SettingDetail'
import Releases from './pages/Releases'
import ReleaseDetail from './pages/ReleaseDetail'
import AnnouncementDetail from './pages/AnnouncementDetail'
import Glossary from './pages/Glossary'
import Options from './pages/Options'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="registry" element={<Registry />} />
        <Route path="features/:featureId" element={<FeatureDetail />} />
        <Route path="options" element={<Options />} />
        <Route path="options/:optionId" element={<OptionDetail />} />
        <Route path="settings" element={<Settings />} />
        <Route path="settings/:settingId" element={<SettingDetail />} />
        <Route path="releases" element={<Releases />} />
        <Route path="releases/:contentId" element={<ReleaseDetail />} />
        <Route path="announcements/:id" element={<AnnouncementDetail />} />
        <Route path="glossary" element={<Glossary />} />
        {/* Redirects from old routes */}
        <Route path="features" element={<Navigate to="/registry" replace />} />
      </Route>
    </Routes>
  )
}

export default App
