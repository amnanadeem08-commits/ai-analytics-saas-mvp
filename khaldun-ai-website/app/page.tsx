import { ContactSection } from "@/components/ContactSection";
import { EngineeringSection } from "@/components/EngineeringSection";
import { Hero } from "@/components/Hero";
import { HowWeWork } from "@/components/HowWeWork";
import { PlatformSection } from "@/components/PlatformSection";
import { ProductSignalFeed } from "@/components/ProductSignalFeed";
import { ProofSection } from "@/components/ProofSection";
import { ServicesSection } from "@/components/ServicesSection";
import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import { WhySection } from "@/components/WhySection";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main id="main-content">
        <Hero />
        <ProductSignalFeed />
        <PlatformSection />
        <WhySection />
        <EngineeringSection />
        <ServicesSection />
        <HowWeWork />
        <ProofSection />
        <ContactSection />
      </main>
      <SiteFooter />
    </>
  );
}
