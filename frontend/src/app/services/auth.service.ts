import { Injectable, PLATFORM_ID, Inject, isDevMode } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';
import { Router } from '@angular/router';

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private apiUrl = (isDevMode() ? 'http://localhost:8000' : '') + '/auth';
    private currentUserSubject = new BehaviorSubject<any>(null);
    public currentUser$ = this.currentUserSubject.asObservable();
    private isBrowser: boolean;

    public get currentUserValue(): any {
        return this.currentUserSubject.value;
    }

    constructor(
        private http: HttpClient,
        private router: Router,
        @Inject(PLATFORM_ID) platformId: Object
    ) {
        this.isBrowser = isPlatformBrowser(platformId);
        if (this.isBrowser) {
            const user = localStorage.getItem('currentUser');
            if (user) {
                this.currentUserSubject.next(JSON.parse(user));
            }
        }
    }

    signup(userData: any): Observable<any> {
        return this.http.post(`${this.apiUrl}/signup`, userData).pipe(
            tap(response => {
                // Automatically login after signup? 
                // For now, just return success, component handles redirect to signin
            })
        );
    }

    signin(credentials: any): Observable<any> {
        return this.http.post<any>(`${this.apiUrl}/signin`, credentials).pipe(
            tap(response => {
                if (response.access_token && this.isBrowser) {
                    localStorage.setItem('access_token', response.access_token);
                    const user = {
                        name: response.user_name,
                        email: credentials.email
                    };
                    localStorage.setItem('currentUser', JSON.stringify(user));
                    this.currentUserSubject.next(user);
                }
            })
        );
    }

    logout(): void {
        if (this.isBrowser) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('currentUser');
        }
        this.currentUserSubject.next(null);
        this.router.navigate(['/signin']);
    }

    getToken(): string | null {
        if (this.isBrowser) {
            return localStorage.getItem('access_token');
        }
        return null;
    }

    isAuthenticated(): boolean {
        return !!this.getToken();
    }
}
