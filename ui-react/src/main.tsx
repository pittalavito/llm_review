import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';

// Global styles, same order as ui/index.html (graphrun last among sections so
// its .badge definition wins, as in the vanilla UI).
import './styles/variables.css';
import './styles/reset.css';
import './styles/layout.css';
import './styles/components.css';
import './styles/health.css';
import './styles/test-llm.css';
import './styles/test-agent.css';
import './styles/test-rag.css';
import './styles/comparison.css';
import './styles/graphrun.css';
import './styles/swagger.css';

import AppLayout from './layout/AppLayout';
import Health from './sections/Health';
import TestLlm from './sections/TestLlm';
import Prompts from './sections/Prompts';
import Storico from './sections/Storico';
import TestAgent from './sections/TestAgent';
import TestRag from './sections/TestRag';
import GraphRun from './sections/GraphRun';
import Compare from './sections/Compare';
import Swagger from './sections/Swagger';

const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <AppLayout />,
      children: [
        { index: true, element: <Navigate to="/health" replace /> },
        { path: 'health', element: <Health /> },
        { path: 'test-llm', element: <TestLlm /> },
        { path: 'test-agent', element: <TestAgent /> },
        { path: 'test-rag', element: <TestRag /> },
        { path: 'swagger', element: <Swagger /> },
        { path: 'prompts', element: <Prompts /> },
        { path: 'graph-run', element: <GraphRun /> },
        { path: 'storico', element: <Storico /> },
        { path: 'comparison', element: <Compare /> },
        { path: '*', element: <Navigate to="/health" replace /> },
      ],
    },
  ],
  { basename: '/v2' },
);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
