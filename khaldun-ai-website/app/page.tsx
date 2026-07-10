import { ContactSection } from "@/components/ContactSection";
import { Hero } from "@/components/Hero";
import { HowWeWork } from "@/components/HowWeWork";
import { ProductSignalFeed } from "@/components/ProductSignalFeed";
import { ProofSection } from "@/components/ProofSection";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <Hero />
        <ProductSignalFeed />
        <HowWeWork />
        <ProofSection />
        <ContactSection />
      </main>
      <SiteFooter />
    </>
  );
}
