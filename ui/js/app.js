/**
 * app.js — entry point.
 *
 * Registers all sections, initialises the router, and navigates
 * to the default section. This is the only file that knows which
 * sections exist — adding a new section only requires editing here.
 */

import { registerSection, navigate, initRouter } from './router.js';
import { render as graphRender, mount as graphMount } from './sections/graph.js';
import { render as healthRender, mount as healthMount } from './sections/health.js';
import { render as openReviewRender, mount as openReviewMount } from './sections/openreview.js';
import { render as reviewRender, mount as reviewMount } from './sections/review.js';
import { render as testLlmRender, mount as testLlmMount } from './sections/testllm.js';
import { render as testAgentRender, mount as testAgentMount } from './sections/testagent.js';

registerSection('health', { render: healthRender, mount: healthMount });
registerSection('openreview', { render: openReviewRender, mount: openReviewMount });
registerSection('test-llm', { render: testLlmRender, mount: testLlmMount });
registerSection('test-agent', { render: testAgentRender, mount: testAgentMount });
registerSection('graph', { render: graphRender, mount: graphMount });
registerSection('review', { render: reviewRender, mount: reviewMount });

initRouter();
navigate('health');
