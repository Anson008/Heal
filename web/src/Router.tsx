import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Route = "/" | "/tool";

const NavigateContext = createContext<(to: Route) => void>(() => {});

function resolveRoute(routes: Partial<Record<Route, ReactNode>>): Route {
  const path = window.location.pathname;
  return path in routes ? (path as Route) : "/";
}

/**
 * Minimal client-side router: swaps between a small, fixed set of routes
 * using the History API, no external dependency required. `routes` maps
 * a path to the element to render for it; anything else falls back to "/".
 */
function Router({ routes }: { routes: Partial<Record<Route, ReactNode>> }) {
  const [route, setRoute] = useState<Route>(() => resolveRoute(routes));

  useEffect(() => {
    const onPopState = () => setRoute(resolveRoute(routes));
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [routes]);

  function navigate(to: Route) {
    if (to !== window.location.pathname) {
      window.history.pushState({}, "", to);
    }
    window.scrollTo(0, 0);
    setRoute(to);
  }

  return (
    <NavigateContext.Provider value={navigate}>
      {routes[route]}
    </NavigateContext.Provider>
  );
}

export function useNavigate() {
  return useContext(NavigateContext);
}

export default Router;
