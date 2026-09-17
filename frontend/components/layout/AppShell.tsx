import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-cream-100">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
