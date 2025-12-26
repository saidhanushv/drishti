import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sign-in',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './sign-in.component.html',
  styleUrl: './sign-in.component.css'
})
export class SignInComponent {
  signInForm: FormGroup;
  showPassword = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    this.signInForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]]
    });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (this.signInForm.valid) {
      const { email, password } = this.signInForm.value;

      this.authService.signin({ email, password }).subscribe({
        next: (response) => {
          console.log('Sign In Successful', response);
          this.router.navigate(['/dashboard']);
        },
        error: (error) => {
          console.error('Sign In Error', error);
          this.errorMessage = error.error?.detail || 'Invalid email or password';
        }
      });
    } else {
      this.errorMessage = 'Please fill in all required fields correctly.';
    }
  }

  signInWithGoogle(): void {
    // TODO: Implement Google OAuth
    console.log('Google Sign In clicked');
    alert('Google Sign In will be implemented with OAuth 2.0');
  }

  get email() {
    return this.signInForm.get('email');
  }

  get password() {
    return this.signInForm.get('password');
  }
}
