import Head from 'next/head'
import Link from 'next/link'

export default function PrivacyPolicy() {
  return (
    <div className="bg-[#020202] text-neutral-300 min-h-screen font-sans flex flex-col items-center justify-center p-6 md:p-12">
      <Head>
        <title>Privacy Policy — Fusion OS</title>
        <meta name="description" content="Privacy Policy for Fusion OS Boardroom Diligence Swarm" />
      </Head>

      <div className="max-w-2xl w-full border border-white/[0.08] bg-[#0a0a0a] p-8 md:p-12 rounded-3xl shadow-2xl relative">
        <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-accent via-emerald-400 to-accent" />
        
        <h1 className="text-2xl font-bold text-white mb-2 font-mono">Privacy Policy</h1>
        <p className="text-xs text-neutral-500 font-mono mb-8">Last Updated: June 17, 2026</p>

        <div className="space-y-6 text-sm leading-relaxed">
          <section>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono mb-2">1. Overview</h2>
            <p>
              At Fusion OS, we are committed to protecting your privacy. This Privacy Policy describes how we handle and protect your information when you log in and use our service.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono mb-2">2. Information We Access</h2>
            <p>
              When you authenticate using Google Sign-In, we access only the basic profile information provided by Google's non-sensitive OAuth scope:
            </p>
            <ul className="list-disc pl-5 mt-2 space-y-1">
              <li>Your email address (to identify your account)</li>
              <li>Your name (to customize your interface)</li>
              <li>Your profile picture (to display your avatar in the sidebar)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono mb-2">3. How We Use Your Data</h2>
            <p>
              We use your email address and authentication token solely to isolate your workspace and deal history. This ensures that no other user can see your diligence workflows, documents, or agent logs.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono mb-2">4. Third-Party Sharing</h2>
            <p>
              We do not sell, rent, or share your personal data with any third parties. All communication with our backend agents is secured and private.
            </p>
          </section>

          <section>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono mb-2">5. Data Deletion</h2>
            <p>
              If you wish to delete your account or wipe your private workspace data, you can request account deletion by contacting support.
            </p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t border-white/[0.06] flex justify-between items-center text-xs">
          <Link href="/" className="text-accent hover:underline font-mono">
            &larr; Back to Boardroom
          </Link>
          <span className="text-neutral-600 font-mono">Fusion OS</span>
        </div>
      </div>
    </div>
  )
}
