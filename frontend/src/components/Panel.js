export function Panel({ children, className = "", ...rest }) {
  return (
    <div className={`panel overflow-hidden ${className}`} {...rest}>
      {children}
    </div>
  );
}

export function PanelHeader({ children }) {
  return <div className="panel-header">{children}</div>;
}

export function PanelTitle({ children }) {
  return <div className="text-sm font-medium">{children}</div>;
}
