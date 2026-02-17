import { Footer } from "@/components/layout/footer";

export default function MarketingLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <>
      {children}
      <Footer />
    </>
  );
}
