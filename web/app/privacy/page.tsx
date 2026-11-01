import Link from "next/link";
import { PageHeading } from "@/components/ui";

export const metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <>
      <PageHeading
        eyebrow="YOUR DATA"
        title="Privacy, in plain language."
        description="Last updated 1 November 2026."
      />
      <article className="panel policy-page">
        <h2>What I collect</h2>
        <p>
          Dar Traffic does not ask for your name, an account or your location.
          The road coordinates shown here describe monitored corridors, not
          where you are. There is no advertising or analytics code in the app.
        </p>
        <h2>Your saved roads</h2>
        <p>
          Saved corridor IDs stay in your browser’s local storage. They are not
          sent to me. You can remove a saved road with its bookmark button or
          clear this website’s stored data in your browser settings.
        </p>
        <h2>Services your browser contacts</h2>
        <p>
          Vercel hosts the website. Google Cloud handles on-demand estimates and permitted history,
          and Google Fonts supplies the fonts. Those services receive connection
          information such as your IP address and request details. Their own
          policies govern how they handle it:
        </p>
        <ul>
          <li><a href="https://vercel.com/legal/privacy-policy">Vercel Privacy Policy</a></li>
          <li><a href="https://policies.google.com/privacy">Google Privacy Policy</a></li>
        </ul>
        <p>
          Opening a Google Maps directions link takes you to Google, where its
          privacy policy and terms apply. The app does not read your Google
          account or start location tracking.
        </p>
        <h2>Traffic records and downloads</h2>
        <p>
          Live Google estimates describe configured road segments and are not saved to the traffic database. Private usage counters limit requests without storing traffic content. A CSV download,
          when available, is created in your browser and saved on your device.
          It does not upload your own files. Data-source and retention limits
          are explained on the <Link href="/history/">History page</Link>.
        </p>
        <h2>Questions or corrections</h2>
        <p>
          You can raise a privacy concern through the <a href="https://github.com/jemmziray-tech/Dar_Traffic_Project/issues">project’s GitHub issues</a>.
          Please do not post personal location records or other sensitive
          information in a public issue. I will update this page when the way
          the project handles data changes.
        </p>
      </article>
    </>
  );
}
