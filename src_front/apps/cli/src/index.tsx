import React from "react";
import { createRequire } from "module";

const req = createRequire(import.meta.url);
const cjsReact = req("react");
if (cjsReact && !cjsReact.ReactSharedInternals) {
  cjsReact.ReactSharedInternals =
    cjsReact.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE ||
    cjsReact.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
}

import { render } from "ink";
import { App } from "./App";

render(<App />);
