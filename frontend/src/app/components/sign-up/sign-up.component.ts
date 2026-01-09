import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-sign-up',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './sign-up.component.html',
  styleUrl: './sign-up.component.css'
})
export class SignUpComponent {
  signUpForm: FormGroup;
  showPassword = false;
  errorMessage = '';

  workFieldOptions = [
    'Student',
    'Engineer',
    'Consultant',
    'RGM Strategist',
    'Data Analyst',
    'Product Manager',
    'Business Analyst',
    'Other'
  ];

  sourceOptions = [
    'Reddit',
    'X (Twitter)',
    'Instagram',
    'Google',
    'LinkedIn',
    'Friend Referral',
    'Other'
  ];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private authService: AuthService
  ) {
    this.signUpForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, this.passwordValidator]],
      workField: ['', Validators.required],
      source: ['', Validators.required]
    });
  }

  // Custom password validator
  passwordValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    if (!value) return null;

    const hasMinLength = value.length >= 8;
    const hasUpperCase = /[A-Z]/.test(value);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(value);

    const passwordValid = hasMinLength && hasUpperCase && hasSpecialChar;

    return passwordValid ? null : {
      passwordStrength: {
        hasMinLength,
        hasUpperCase,
        hasSpecialChar
      }
    };
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  onSubmit(): void {
    if (this.signUpForm.valid) {
      const formValue = this.signUpForm.value;

      // Map frontend camelCase to backend snake_case
      const payload = {
        name: formValue.name,
        email: formValue.email,
        password: formValue.password,
        work_field: formValue.workField,
        source: formValue.source
      };

      this.authService.signup(payload).subscribe({
        next: (response) => {
          console.log('Sign Up Successful', response);
          alert('Account created successfully! Please sign in.');
          this.router.navigate(['/signin']);
        },
        error: (error) => {
          console.error('Sign Up Error', error);
          // Handle FastAPI validation errors (which return an array of details)
          if (Array.isArray(error.error?.detail)) {
            this.errorMessage = error.error.detail.map((e: any) => e.msg).join(', ');
          } else {
            this.errorMessage = error.error?.detail || 'Registration failed. Please try again.';
          }
        }
      });
    } else {
      this.errorMessage = 'Please fill in all required fields correctly.';
    }
  }

  signUpWithGoogle(): void {
    // TODO: Implement Google OAuth
    console.log('Google Sign Up clicked');
    alert('Google Sign Up will be implemented with OAuth 2.0');
  }

  get name() {
    return this.signUpForm.get('name');
  }

  get email() {
    return this.signUpForm.get('email');
  }

  get password() {
    return this.signUpForm.get('password');
  }

  get workField() {
    return this.signUpForm.get('workField');
  }

  get source() {
    return this.signUpForm.get('source');
  }

  get passwordErrors() {
    return this.password?.errors?.['passwordStrength'];
  }
}
