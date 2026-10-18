// Guarded (CODEOWNERS). check:boundaries runs this config (docs/adr/0102).
/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular",
      comment: "A circular import makes the order of evaluation fragile.",
      severity: "error",
      from: {},
      to: { circular: true },
    },
    {
      name: "feature-isolation",
      comment: "A feature folder in components/ does not import another feature folder.",
      severity: "error",
      from: { path: "^src/components/([^/]+)/" },
      to: { path: "^src/components/([^/]+)/", pathNot: "^src/components/$1/" },
    },
    {
      name: "lib-and-types-have-no-ui",
      comment: "lib/ and types/ are below the UI. They do not import app/, components/, or hooks/.",
      severity: "error",
      from: { path: "^src/(lib|types)/" },
      to: { path: "^src/(app|components|hooks)/" },
    },
    {
      name: "not-to-unresolvable",
      severity: "error",
      from: {},
      to: { couldNotResolve: true },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
  },
};
