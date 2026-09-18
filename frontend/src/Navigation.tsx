type NavigationProps = {
  active: "citizen" | "operator";
};

export function Navigation({ active }: NavigationProps) {
  // Hash links keep navigation inside the existing lightweight routing model
  // without exposing credentials or introducing a separate client router.
  return <nav className="app-nav" aria-label="Primary navigation"><a className="app-nav-brand" href="#/">CivicLens</a><div className="app-nav-links"><a className={active === "citizen" ? "app-nav-link active" : "app-nav-link"} href="#/" aria-current={active === "citizen" ? "page" : undefined}>Citizen Reporting</a><a className={active === "operator" ? "app-nav-link active" : "app-nav-link"} href="#/operator" aria-current={active === "operator" ? "page" : undefined}>Operator Console</a></div></nav>;
}
