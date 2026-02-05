import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Features from './pages/Features'
import FeatureDetail from './pages/FeatureDetail'
import Options from './pages/Options'
import OptionDetail from './pages/OptionDetail'
import Releases from './pages/Releases'
import ReleaseDetail from './pages/ReleaseDetail'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="features" element={<Features />} />
        <Route path="features/:featureId" element={<FeatureDetail />} />
        <Route path="options" element={<Options />} />
        <Route path="options/:optionId" element={<OptionDetail />} />
        <Route path="releases" element={<Releases />} />
        <Route path="releases/:contentId" element={<ReleaseDetail />} />
      </Route>
    </Routes>
  )
}

export default App
