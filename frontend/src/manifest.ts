// What this addon adds to AYON's web UI. AYON loads this module at startup (it is exposed as
// ./manifest and listed in frontend_modules in server/__init__.py), so keep it to descriptions:
// every component is a dynamic import that AYON loads when its slot needs it.
//
// Add more with the other helpers of @ynput/ayon-addon/manifest (detailsPanelTab, headerItem,
// entityMenuItem, tableColumn, ...): `yarn ayon-addon slots` lists them all.
import { defineAddon, studioPage } from "@ynput/ayon-addon/manifest";

export default defineAddon({
  contributes: [
    // a tab on the dashboard, at /dashboard/my_addon
    studioPage({
      id: "my_addon",
      title: "My Addon",
      component: () => import("./pages/MyStudioPage"),
    }),
  ],
});
