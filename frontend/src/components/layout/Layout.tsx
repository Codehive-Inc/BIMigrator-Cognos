const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar onMenuToggle={/* your toggle function */} />
      <div className="pt-16"> {/* Added padding-top to account for fixed navbar */}
        {children}
      </div>
    </div>
  );
}; 