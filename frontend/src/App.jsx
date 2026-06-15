import { Route, Routes } from 'react-router-dom'

import Header from './components/Header'
import JobStatusBanner from './components/JobStatusBanner'
import { JobStatusProvider } from './hooks/useJobStatus'

import HomePage from './pages/HomePage'

import BrowsePage from './pages/BrowsePage'

import MediaDetailPage from './pages/MediaDetailPage'
import EpisodePage from './pages/EpisodePage'

import PersonPage from './pages/PersonPage'

import SettingsPage from './pages/SettingsPage'
import JobsPage from './pages/JobsPage'
import AddMediaPage from './pages/AddMediaPage'



export default function App() {

  return (

    <JobStatusProvider>

    <div className="app">

      <Header />

      <JobStatusBanner />

      <main className="main">

        <Routes>

          <Route path="/" element={<HomePage />} />

          <Route path="/movies" element={<BrowsePage defaultType="movie" title="Movies" />} />

          <Route path="/tv" element={<BrowsePage defaultType="tv" title="TV Shows" />} />

          <Route path="/search" element={<BrowsePage title="Search" />} />

          <Route path="/media/:id/season/:season/episode/:episode" element={<EpisodePage />} />

          <Route path="/media/:id" element={<MediaDetailPage />} />

          <Route path="/people/:id" element={<PersonPage />} />

          <Route path="/add" element={<AddMediaPage />} />

          <Route path="/settings" element={<SettingsPage />} />

          <Route path="/jobs" element={<JobsPage />} />

        </Routes>

      </main>

    </div>

    </JobStatusProvider>

  )

}

