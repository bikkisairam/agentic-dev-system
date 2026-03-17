import { Component, inject, signal } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { ApiService } from './api.service';

type StageStatus = 'idle' | 'running' | 'success' | 'error';

interface Stage {
  id: string;
  label: string;
  icon: string;
  status: StageStatus;
  output: any;
}

@Component({
  selector: 'app-root',
  imports: [CommonModule, HttpClientModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  private api = inject(ApiService);

  pipelineRunning = signal(false);
  serverOnline = signal<boolean | null>(null);

  stages = signal<Stage[]>([
    { id: 'plan',     label: 'Plan',     icon: '📋', status: 'idle', output: null },
    { id: 'build',    label: 'Build',    icon: '🔨', status: 'idle', output: null },
    { id: 'check',    label: 'Check',    icon: '🧪', status: 'idle', output: null },
    { id: 'evaluate', label: 'Evaluate', icon: '✅', status: 'idle', output: null },
    { id: 'push',     label: 'Push',     icon: '📤', status: 'idle', output: null },
  ]);

  ngOnInit() { this.pingServer(); }

  pingServer() {
    this.api.getStatus().subscribe({
      next: () => this.serverOnline.set(true),
      error: () => this.serverOnline.set(false)
    });
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
    this.resetStages();
    this.pipelineRunning.set(true);

    const stageOrder = ['plan', 'build', 'check', 'evaluate', 'push'];

    // Set first stage to running immediately
    this.setStageStatus('plan', 'running');

    const es = new EventSource('http://localhost:8005/stream');

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.done) {
        es.close();
        this.pipelineRunning.set(false);
        return;
      }

      // Mark current stage complete
      this.setStageStatus(data.stage, data.status, data.output);

      // Set next stage to running
      const nextIndex = stageOrder.indexOf(data.stage) + 1;
      if (nextIndex < stageOrder.length) {
        this.setStageStatus(stageOrder[nextIndex], 'running');
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

  runPlan() {
    this.setStageStatus('plan', 'running');
    this.api.getStory().subscribe({
      next: (res) => this.setStageStatus('plan', 'success', res.story ?? res),
      error: (err) => this.setStageStatus('plan', 'error', err.error)
    });
  }

  runBuild() {
    this.setStageStatus('build', 'running');
    this.api.build().subscribe({
      next: (res) => this.setStageStatus('build', 'success', res.code ?? res),
      error: (err) => this.setStageStatus('build', 'error', err.error)
    });
  }

  runCheck() {
    this.setStageStatus('check', 'running');
    this.api.test().subscribe({
      next: (res) => this.setStageStatus('check', res.passed ? 'success' : 'error', res),
      error: (err) => this.setStageStatus('check', 'error', err.error)
    });
  }

  runEvaluate() {
    this.setStageStatus('evaluate', 'running');
    this.api.commit().subscribe({
      next: (res) => this.setStageStatus('evaluate', res.status === 'committed' ? 'success' : 'error', res),
      error: (err) => this.setStageStatus('evaluate', 'error', err.error)
    });
  }

  runPush() {
    this.setStageStatus('push', 'running');
    this.api.push().subscribe({
      next: (res) => this.setStageStatus('push', res.status === 'pushed' ? 'success' : 'error', res),
      error: (err) => this.setStageStatus('push', 'error', err.error)
    });
  }

  triggerStage(stage: Stage, event: Event) {
    event.stopPropagation();
    const actions: Record<string, () => void> = {
      plan:     () => this.runPlan(),
      build:    () => this.runBuild(),
      check:    () => this.runCheck(),
      evaluate: () => this.runEvaluate(),
      push:     () => this.runPush(),
    };
    actions[stage.id]?.();
  }

  get completedCount(): number {
    return this.stages().filter(s => s.status === 'success').length;
  }

  get totalStages(): number {
    return this.stages().length;
  }

  get hasAnyOutput(): boolean {
    return this.stages().some(s => s.output !== null);
  }

  stageOf(id: string): Stage {
    return this.stages().find(s => s.id === id)!;
  }

  checkEntries(checks: Record<string, boolean>): { key: string; pass: boolean }[] {
    return Object.entries(checks ?? {}).map(([key, pass]) => ({ key, pass }));
  }

  formatJson(obj: any): string {
    return JSON.stringify(obj, null, 2);
  }
}
