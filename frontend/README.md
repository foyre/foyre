# foyre-frontend

The Foyre web UI — a React + TypeScript single-page app built with Vite.

For a product overview and quick start, see the
[root README](../README.md).

## Stack

- React 18 + TypeScript
- [Vite](https://vitejs.dev/)
- [React Router](https://reactrouter.com/) v6

No global state library, no UI kit — the app ships a small, hand-rolled
design system in `styles.css` and a handful of shared components.

## Run locally

From the repo root: `make front-install` then `make front`. Or manually:

```bash
npm install
npm run dev
```

The dev server proxies `/api` to <http://localhost:8000>, so run the
backend (`make run`) alongside.

## Layout

```
src/
  api/               fetch wrapper, error helpers, typed API modules
  auth/              AuthContext and useAuth hook
  components/        Layout, NavBar, UserMenu, FormField, badges
  features/
    intakeForm/      Schema-driven intake form
    comments/        Comment list + composer
    history/         History list
    requestDetail/   Read-only payload view
    validation/      Validation environment card + kubeconfig callout
    settings/        User management, host cluster config, password form,
                     role descriptions
    requestActions.ts  Per-role status transitions (reviewer actions)
  pages/             Top-level routes
    admin/           Admin sub-pages (Users, Validation environments)
  router.tsx         Route definitions + auth guards
  styles.css         Global styles / design tokens
  types/domain.ts    Shared TypeScript types mirroring backend enums/DTOs
```

## Scripts

| Command          | Effect                                 |
|------------------|----------------------------------------|
| `npm run dev`    | Start the Vite dev server              |
| `npm run build`  | Typecheck and produce a production bundle |
| `npm run preview`| Serve the production bundle locally    |
