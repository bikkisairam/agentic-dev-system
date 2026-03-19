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

  stages = signal<Stage[]>([
    { id: 'prime',    label: 'Prime',    icon: '📋', status: 'idle', output: null, parallel: false },
    { id: 'forge',    label: 'Forge',    icon: '⚒️',  status: 'idle', output: null, parallel: false },
    { id: 'gate',     label: 'Gate',     icon: '🧪', status: 'idle', output: null, parallel: true  },
    { id: 'sentinel', label: 'Sentinel', icon: '🛡️', status: 'idle', output: null, parallel: true  },
    { id: 'conduit',  label: 'Conduit',  icon: '🔁', status: 'idle', output: null, parallel: true  },
    { id: 'scribe',   label: 'Scribe',   icon: '📝', status: 'idle', output: null, parallel: false },
  ]);

  ngOnInit() {
    this.pingServer();
    this.loadTickets();
  }

  pingServer() {
    this.api.getStatus().subscribe({
      next:  () => this.serverOnline.set(true),
      error: () => this.serverOnline.set(false),
    });
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
    this.resetStages();
  }

  setStageStatus(id: string, status: StageStatus, output: any = null) {
    this.stages.update(stages =>
      stages.map(s => s.id === id ? { ...s, status, output } : s)
    );
  }

  resetStages() {
    this.stages.update(stages => stages.map(s => ({ ...s, status: 'idle', output: null })));
  }

  runFullPipeline() {
    if (!this.ticketId().trim()) return;
    this.resetStages();
    this.pipelineRunning.set(true);
    this.setStageStatus('prime', 'running');

    let parallelResolved = 0;
    const es = new EventSource(this.api.paceStreamUrl(this.ticketId()));

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.done) {
        es.close();
        this.pipelineRunning.set(false);
        return;
      }

      const stage  = data.stage as string;
      const status = data.status as StageStatus;

      this.setStageStatus(stage, status, data.output);

      if (stage === 'prime' && status === 'success') {
        this.setStageStatus('forge', 'running');
      } else if (stage === 'forge') {
        this.setStageStatus('gate',     'running');
        this.setStageStatus('sentinel', 'running');
        this.setStageStatus('conduit',  'running');
      } else if (PARALLEL_STAGES.has(stage)) {
        parallelResolved++;
        if (parallelResolved === 3) {
          this.setStageStatus('scribe', 'running');
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

  // ── Helpers ────────────────────────────────────────────────────────────────

  get parallelStages(): Stage[] { return this.stages().filter(s => s.parallel); }
  get completedCount(): number  { return this.stages().filter(s => s.status === 'success').length; }
  get totalStages(): number     { return this.stages().length; }

  stageOf(id: string): Stage {
    return this.stages().find(s => s.id === id)!;
  }

  formatJson(obj: any): string {
    return JSON.stringify(obj, null, 2);
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
