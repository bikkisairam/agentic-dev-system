import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const BASE = 'http://localhost:8005';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  getStatus(): Observable<any> {
    return this.http.get(`${BASE}/`);
  }

  getStory(ticketId: string = 'JIRA-101'): Observable<any> {
    return this.http.get(`${BASE}/jira-story`, { params: { ticket_id: ticketId } });
  }

  getTickets(): Observable<any> {
    return this.http.get(`${BASE}/jira/tickets`);
  }

  // New PACE pipeline
  paceRun(ticketId: string): Observable<any> {
    return this.http.post(`${BASE}/pace/run`, {}, { params: { ticket_id: ticketId } });
  }

  paceStreamUrl(ticketId: string): string {
    return `${BASE}/pace/stream?ticket_id=${encodeURIComponent(ticketId)}`;
  }

  paceStatus(): Observable<any> {
    return this.http.get(`${BASE}/pace/status`);
  }
}
