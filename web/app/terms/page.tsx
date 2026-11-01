import Link from "next/link";
import { PageHeading } from "@/components/ui";

export const metadata = { title: "Terms of use" };

export default function TermsPage() {
  return (
    <>
      <PageHeading
        eyebrow="USING DAR TRAFFIC"
        title="A few things to know."
        description="Last updated 31 October 2026."
      />
      <article className="panel policy-page">
        <h2>What this project offers</h2>
        <p>
          I built Dar Traffic to make traffic estimates for selected corridors
          in Dar es Salaam easier to understand. Coverage is limited, updates
          can be delayed and estimates can be wrong. Check the observation time
          and use your own judgement before travelling.
        </p>
        <h2>Use it safely</h2>
        <p>
          Do not use the website while driving. Follow road signs, local rules
          and official advice. This is not an emergency service or a traffic
          control system, and it does not guarantee arrival times or route safety.
        </p>
        <h2>Google Maps content</h2>
        <p>
          This application includes Google Maps features and content. By using
          those features or content, you agree to the <a href="https://maps.google.com/help/terms_maps/">Google Maps/Google Earth Additional Terms of Service</a>.
          The <a href="https://policies.google.com/privacy">Google Privacy Policy</a> also applies.
          Provider content remains subject to its own usage restrictions; access
          through this website does not grant permission to archive, resell or
          use it for model training.
        </p>
        <h2>Models and measurements</h2>
        <p>
          The current Google traffic feed contains estimates, not direct sensor
          measurements. No validated forecasting model is serving predictions.
          A future model will need data I have permission to use and an honest
          evaluation on later observations before it appears here.
        </p>
        <h2>Availability and changes</h2>
        <p>
          This is an independently maintained project. I may change features or
          pause a feed when its quality, cost or permissions need attention.
          The website is provided as available, without a promise of uninterrupted
          service or accuracy. Nothing here excludes rights that cannot lawfully
          be excluded.
        </p>
        <h2>Questions</h2>
        <p>
          Report a problem through the <a href="https://github.com/jemmziray-tech/Dar_Traffic_Project/issues">project’s GitHub issues</a>.
          For details about browser storage and service providers, read the <Link href="/privacy/">privacy page</Link>.
        </p>
      </article>
    </>
  );
}
