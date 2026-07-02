/**
 * app.js — entry point.
 *
 * Registers all sections, initialises the router, and navigates
 * to the default section. This is the only file that knows which
 * sections exist — adding a new section only requires editing here.
 */

import { registerSection, navigate, initRouter } from './router.js';
import { render as healthRender, mount as healthMount } from './sections/health.js';
import { render as testLlmRender, mount as testLlmMount } from './sections/testllm.js';
import { render as testAgentRender, mount as testAgentMount } from './sections/testagent.js';
import { render as testRagRender, mount as testRagMount } from './sections/testrag.js';
import { render as graphRunRender, mount as graphRunMount } from './sections/graphrun.js';
import { render as storicoRender, mount as storicoMount } from './sections/storico.js';
import { render as compareRender, mount as compareMount } from './sections/compare.js';

registerSection('health', { render: healthRender, mount: healthMount });
registerSection('test-llm', { render: testLlmRender, mount: testLlmMount });
registerSection('test-agent', { render: testAgentRender, mount: testAgentMount });
registerSection('test-rag', { render: testRagRender, mount: testRagMount });
registerSection('graph-run', { render: graphRunRender, mount: graphRunMount });
registerSection('storico', { render: storicoRender, mount: storicoMount });
registerSection('comparison', { render: compareRender, mount: compareMount });

initRouter();
navigate('health');
