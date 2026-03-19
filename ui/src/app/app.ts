import { Component, inject, signal } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from './api.service';

type StageStatus = 'idle' | 'running' | 'success' | 'error';

interface Stage {
  id: string;
  label: string;
  icon: string;
  status: StageStatus;
  output: any;
  parallel: boolean;
}

interface JiraTicket {
  id: string;
  title: string;
  status: string;
  priority: string;
}

const PARALLEL_STAGES = new Set(['gate', 'sentinel', 'conduit']);

@Component({
  selector: 'app-root',
  imports: [CommonModule, HttpClientModule, FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private api = inject(ApiService);

  pipelineRunning = signal(false);
  serverOnline    = signal<boolean | null>(null);
  ticketId        = signal('');
  selectedTicket  = signal<JiraTicket | null>(null);
  tickets         = signal<JiraTicket[]>([]);
  ticketsLoading  = signal(false);

  // Per-ticket stage history (board table state)
  ticketStages = signal<Record<string, Stage[]>>({});

  // Settings panel
  showSettings      = signal(false);
  settingsProvider  = signal('claude');
  settingsApiKey    = signal('');
  settingsApiKeySet = signal(false);
  settingsSaved     = signal(false);

  readonly providers = [
    { value: 'claude',  label: 'Claude (Anthropic)',  placeholder: 'sk-ant-api03-...' },
    { value: 'groq',    label: 'Groq (Free)',          placeholder: 'gsk_...' },
    { value: 'openai',  label: 'OpenAI GPT-4o-mini',  placeholder: 'sk-...' },
    { value: 'ollama',  label: 'Ollama (Local)',       placeholder: 'No key needed' },
  ];

  // Main stages signal — tracks the currently selected ticket's live stages.
  // Used by the sidebar nav and result blocks.
  stages = signal<Stage[]>(this.makeDefaultStages());

  ngOnInit() {
    this.pingServer();
    this.loadTickets();
    this.loadLLMSettings();
  }

  makeDefaultStages(): Stage[] {
    return [
      { id: 'prime',    label: 'Prime',    icon: '📋', status: 'idle', output: null, parallel: false },
      { id: 'forge',    label: 'Forge',    icon: '⚒️',  status: 'idle', output: null, parallel: false },
      { id: 'gate',     label: 'Gate',     icon: '🧪', status: 'idle', output: null, parallel: true  },
      { id: 'sentinel', label: 'Sentinel', icon: '🛡️', status: 'idle', output: null, parallel: true  },
      { id: 'conduit',  label: 'Conduit',  icon: '🔁', status: 'idle', output: null, parallel: true  },
      { id: 'scribe',   label: 'Scribe',   icon: '📝', status: 'idle', output: null, parallel: false },
    ];
  }

  pingServer() {
    this.api.getStatus().subscribe({
      next:  () => this.serverOnline.set(true),
      error: () => this.serverOnline.set(false),
    });
  }

  loadLLMSettings() {
    this.api.getLLMSettings().subscribe({
      next: (res) => {
        this.settingsProvider.set(res.provider);
        this.settingsApiKeySet.set(res.api_key_set);
      },
      error: () => {}
    });
  }

  saveLLMSettings() {
    this.api.saveLLMSettings(this.settingsProvider(), this.settingsApiKey()).subscribe({
      next: () => {
        this.settingsApiKeySet.set(true);
        this.settingsApiKey.set('');
        this.settingsSaved.set(true);
        setTimeout(() => this.settingsSaved.set(false), 2500);
      },
      error: () => {}
    });
  }

  get currentProvider() {
    return this.providers.find(p => p.value === this.settingsProvider()) ?? this.providers[0];
  }

  loadTickets() {
    this.ticketsLoading.set(true);
    this.api.getTickets().subscribe({
      next: (res) => {
        this.tickets.set(res.tickets ?? []);
        this.ticketsLoading.set(false);
      },
      error: () => this.ticketsLoading.set(false),
    });
  }

  selectTicket(ticket: JiraTicket) {
    this.selectedTicket.set(ticket);
    this.ticketId.set(ticket.id);
    // Restore this ticket's saved stages (or reset to idle)
    const saved = this.ticketStages()[ticket.id];
    this.stages.set(saved ? saved.map(s => ({ ...s })) : this.makeDefaultStages());
  }

  // Update a stage for a specific ticket and mirror to the main stages if it's the selected ticket.
  setTicketStageStatus(ticketId: string, stageId: string, status: StageStatus, output: any = null) {
    this.ticketStages.update(record => {
      const existing = record[ticketId] ?? this.makeDefaultStages();
      return {
        ...record,
        [ticketId]: existing.map(s => s.id === stageId ? { ...s, status, output } : s),
      };
    });
    if (this.selectedTicket()?.id === ticketId) {
      this.stages.update(stages => stages.map(s => s.id === stageId ? { ...s, status, output } : s));
    }
  }

  // Legacy helper kept for result blocks.
  setStageStatus(id: string, status: StageStatus, output: any = null) {
    this.stages.update(stages =>
      stages.map(s => s.id === id ? { ...s, status, output } : s)
    );
  }

  resetStages() {
    const tid = this.selectedTicket()?.id;
    const defaults = this.makeDefaultStages();
    this.stages.set(defaults);
    if (tid) {
      this.ticketStages.update(r => ({ ...r, [tid]: this.makeDefaultStages() }));
    }
  }

  runFullPipeline() {
    if (!this.ticketId().trim()) return;
    const runningTicketId = this.ticketId();
    this.resetStages();
    this.pipelineRunning.set(true);
    this.setTicketStageStatus(runningTicketId, 'prime', 'running');

    let parallelResolved = 0;
    const es = new EventSource(this.api.paceStreamUrl(runningTicketId));

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.done) {
        es.close();
        this.pipelineRunning.set(false);
        return;
      }

      const stage  = data.stage as string;
      const status = data.status as StageStatus;

      this.setTicketStageStatus(runningTicketId, stage, status, data.output);

      if (stage === 'prime' && status === 'success') {
        this.setTicketStageStatus(runningTicketId, 'forge', 'running');
      } else if (stage === 'forge') {
        this.setTicketStageStatus(runningTicketId, 'gate',     'running');
        this.setTicketStageStatus(runningTicketId, 'sentinel', 'running');
        this.setTicketStageStatus(runningTicketId, 'conduit',  'running');
      } else if (PARALLEL_STAGES.has(stage)) {
        parallelResolved++;
        if (parallelResolved === 3) {
          this.setTicketStageStatus(runningTicketId, 'scribe', 'running');
          parallelResolved = 0;
        }
      }
    };

    es.onerror = () => {
      es.close();
      this.pipelineRunning.set(false);
      this.stages.update(stages =>
        stages.map(s => s.status === 'running' ? { ...s, status: 'error' } : s)
      );
    };
  }

  // ── Board table helpers ────────────────────────────────────────────────────

  stageOfTicket(ticketId: string, stageId: string): Stage {
    const record = this.ticketStages()[ticketId];
    const stages = record ?? this.makeDefaultStages();
    return stages.find(s => s.id === stageId)!;
  }

  /** Returns 'ship', 'hold', or null (when idle/running). */
  getShipHold(ticketId: string, stageId: string): 'ship' | 'hold' | null {
    const stage = this.stageOfTicket(ticketId, stageId);
    if (stage.status === 'idle' || stage.status === 'running') return null;
    if (stage.status === 'error') return 'hold';
    // success — check decision output for quality-gate stages
    if (stage.output?.decision) {
      return stage.output.decision === 'HOLD' ? 'hold' : 'ship';
    }
    return 'ship';
  }

  // ── Sidebar / result block helpers ────────────────────────────────────────

  get parallelStages(): Stage[] { return this.stages().filter(s => s.parallel); }
  get completedCount(): number  { return this.stages().filter(s => s.status === 'success').length; }
  get totalStages(): number     { return this.stages().length; }

  stageOf(id: string): Stage {
    return this.stages().find(s => s.id === id)!;
  }

  decisionClass(decision: string): string {
    if (decision === 'SHIP' || decision === 'SHIPPED') return 'tag-success';
    if (decision === 'ADVISORY')                       return 'tag-warn';
    return 'tag-error';
  }

  statusBadge(status: string): string {
    const s = status?.toLowerCase();
    if (s === 'to do')       return 'badge-todo';
    if (s === 'in progress') return 'badge-inprogress';
    if (s === 'done')        return 'badge-done';
    return 'badge-todo';
  }
}
