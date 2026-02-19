export default function Glossary() {
  return (
    <div className="animate-fade-in max-w-4xl">
      <header className="mb-8">
        <h1 className="text-title text-zinc-100">Glossary</h1>
        <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
          Reference for feature option terminology, configuration states, and availability labels used throughout Canvas Tracker.
        </p>
      </header>

      <div className="space-y-10">
        {/* Section 1: Lifecycle Stages */}
        <Section title="Lifecycle Stages">
          <div className="card p-5 space-y-4">
            <p className="text-sm text-zinc-400 leading-relaxed">
              Feature <strong className="text-zinc-300">options</strong> (admin toggles) progress through lifecycle stages.
              Feature <strong className="text-zinc-300">settings</strong> (automatic changes) use date-based statuses instead.
            </p>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Feature Option Stages
            </h3>
            <dl className="space-y-4">
              <Definition
                term="Preview"
                color="text-status-preview"
              >
                In active development. Has user groups for feedback. Will eventually graduate to Optional.
              </Definition>
              <Definition
                term="Optional"
                color="text-status-optional"
              >
                Released and available for admin configuration. Admins can enable or disable at account or course level.
                Most features stay here permanently.
              </Definition>
            </dl>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Enforcement
            </h3>
            <dl className="space-y-4">
              <Definition
                term="Will Be Enforced"
                color="text-amber-400"
              >
                An optional feature that Instructure has flagged for future enforcement.
                The toggle will eventually be removed and the feature enabled for everyone
                (e.g., New Quizzes replacing Classic Quizzes).
              </Definition>
            </dl>

            {/* Visual progression */}
            <div className="pt-4 border-t border-zinc-800/50">
              <p className="text-xs font-mono text-zinc-500 mb-3">Progression</p>
              <div className="flex items-center gap-2 flex-wrap text-sm font-mono">
                <span className="px-2.5 py-1 rounded-md bg-status-preview/15 text-status-preview">Preview</span>
                <Arrow />
                <span className="px-2.5 py-1 rounded-md bg-status-optional/15 text-status-optional">Optional</span>
                <Arrow />
                <div className="flex items-center gap-1">
                  <span className="px-2.5 py-1 rounded-md bg-status-optional/15 text-status-optional">Optional</span>
                  <span className="px-1.5 py-0.5 text-xs rounded bg-amber-400/15 text-amber-400">Enforced</span>
                </div>
                <Arrow />
                <span className="px-2.5 py-1 rounded-md bg-surface-3 text-zinc-500">Removed</span>
              </div>
              <p className="mt-3 text-xs text-zinc-500">
                Not all features follow every stage. Many stay optional permanently.
              </p>
            </div>

            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 pt-2">
              Feature Setting Statuses
            </h3>
            <dl className="space-y-4">
              <Definition term="Pending" color="text-status-pending">
                Announced but neither beta nor production date has arrived.
              </Definition>
              <Definition term="Beta" color="text-status-beta">
                Available on the beta environment for testing.
              </Definition>
              <Definition term="Released" color="text-status-released">
                Production date has passed. Active in production for all users.
              </Definition>
            </dl>
          </div>
        </Section>

        {/* Section 2: Configuration States */}
        <Section title="Configuration States">
          <div className="space-y-5">
            {/* Account-level */}
            <div>
              <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-3 px-1">
                Account Level
              </h3>
              <div className="card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800/50">
                      <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider w-56">State</th>
                      <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider">Meaning</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    <ConfigRow state="Enabled / Unlocked" meaning="On by default, subaccounts and courses can override" />
                    <ConfigRow state="Enabled / Locked" meaning="On for everyone; subaccounts and courses cannot override" />
                    <ConfigRow state="Disabled / Unlocked" meaning="Off by default, subaccounts and courses can enable" />
                    <ConfigRow state="Disabled / Locked" meaning="Off for everyone; subaccounts and courses cannot override" />
                    <ConfigRow state="Enabled (account-only)" meaning="On; no lower-level override possible. Lock toggle does not exist" />
                    <ConfigRow state="Disabled (account-only)" meaning="Off; no lower-level override possible. Lock toggle does not exist" />
                  </tbody>
                </table>
              </div>
            </div>

            {/* Course-level */}
            <div>
              <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-zinc-500 mb-3 px-1">
                Course Level
              </h3>
              <div className="card overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-zinc-800/50">
                      <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider w-56">State</th>
                      <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider">Meaning</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/50">
                    <ConfigRow state="Enabled" meaning="On in this course" />
                    <ConfigRow state="Disabled" meaning="Off in this course" />
                  </tbody>
                </table>
              </div>
            </div>

            {/* Explanation */}
            <div className="px-1">
              <p className="text-sm text-zinc-400 leading-relaxed">
                <span className="font-mono text-zinc-300">Locked</span> means the admin chose to prevent lower levels from overriding.{' '}
                <span className="font-mono text-zinc-300">Account-only</span> means the feature does not display at lower levels at all &mdash; there is nothing to lock.
              </p>
            </div>
          </div>
        </Section>

        {/* Section 3: Special Configurations */}
        <Section title="Special Configurations">
          <div className="card p-5">
            <dl className="space-y-4">
              <Definition term="CSM Managed" color="text-signal-amber">
                Must be configured by a Customer Success Manager. Not self-service.
              </Definition>
              <Definition term="LTI Required" color="text-signal-cyan">
                Requires LTI tool configuration, not a standard toggle.
              </Definition>
              <Definition term="User Setting" color="text-signal-violet">
                Per-user preference, not an account or course level setting.
              </Definition>
            </dl>
          </div>
        </Section>

        {/* Section 4: Availability */}
        <Section title="Availability">
          <div className="card p-5 space-y-4">
            <p className="text-sm text-zinc-400 leading-relaxed">
              Availability is derived from <span className="font-mono text-zinc-300">beta_date</span> and{' '}
              <span className="font-mono text-zinc-300">production_date</span> fields. These dates come from
              release and deploy notes, not the canonical feature options page.
            </p>

            <div className="overflow-hidden rounded-md border border-zinc-800/50">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-800/50 bg-surface-3/30">
                    <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider w-40">Label</th>
                    <th className="text-left px-4 py-2.5 text-xs font-mono font-medium text-zinc-500 uppercase tracking-wider">Condition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/50">
                  <tr>
                    <td className="px-4 py-2.5">
                      <span className="pill bg-status-released/15 text-status-released">In Production</span>
                    </td>
                    <td className="px-4 py-2.5 text-zinc-400">production_date has passed</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5">
                      <span className="pill bg-status-beta/15 text-status-beta">In Beta</span>
                    </td>
                    <td className="px-4 py-2.5 text-zinc-400">beta_date has passed, but not yet in production</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-2.5">
                      <span className="pill bg-surface-3 text-zinc-400">Upcoming</span>
                    </td>
                    <td className="px-4 py-2.5 text-zinc-400">Date is in the future</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </Section>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="text-label uppercase text-zinc-400 font-mono mb-4">{title}</h2>
      {children}
    </section>
  )
}

function Definition({
  term,
  color,
  children,
}: {
  term: string
  color: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start gap-4">
      <dt className={`w-24 flex-shrink-0 font-mono text-sm font-medium ${color}`}>{term}</dt>
      <dd className="text-sm text-zinc-400 leading-relaxed">{children}</dd>
    </div>
  )
}

function ConfigRow({ state, meaning }: { state: string; meaning: string }) {
  return (
    <tr>
      <td className="px-4 py-2.5 font-mono text-zinc-300 text-xs">{state}</td>
      <td className="px-4 py-2.5 text-zinc-400">{meaning}</td>
    </tr>
  )
}

function Arrow() {
  return (
    <svg className="w-4 h-4 text-zinc-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  )
}
