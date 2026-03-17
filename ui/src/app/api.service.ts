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

  getStory(): Observable<any> {
    return this.http.get(`${BASE}/jira-story`);
  }

  build(): Observable<any> {
    return this.http.post(`${BASE}/build`, {});
  }

  test(): Observable<any> {
    return this.http.post(`${BASE}/test`, {});
  }

  commit(): Observable<any> {
    return this.http.post(`${BASE}/commit`, {});
  }

  runPace(): Observable<any> {
    return this.http.post(`${BASE}/run`, {});
  }
}
