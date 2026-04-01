import React, { useState } from 'react';
import {
  Container,
  Header,
  Form,
  FormField,
  Input,
  Button,
  SpaceBetween,
  Alert,
  Box
} from '@cloudscape-design/components';
import { AuthError } from './types';

interface NewPasswordFormProps {
  onCompleteNewPassword: (newPassword: string) => Promise<void>;
  isLoading: boolean;
  error?: AuthError | null;
}

interface FormData {
  newPassword: string;
  confirmPassword: string;
}

interface FormErrors {
  newPassword?: string;
  confirmPassword?: string;
}

export const NewPasswordForm: React.FC<NewPasswordFormProps> = ({ 
  onCompleteNewPassword, 
  isLoading, 
  error 
}) => {
  const [formData, setFormData] = useState<FormData>({
    newPassword: '',
    confirmPassword: ''
  });
  
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validatePassword = (password: string): string | undefined => {
    if (!password) {
      return 'Password is required';
    }
    if (password.length < 8) {
      return 'Password must be at least 8 characters long';
    }
    if (!/[A-Z]/.test(password)) {
      return 'Password must contain at least one uppercase letter';
    }
    if (!/[a-z]/.test(password)) {
      return 'Password must contain at least one lowercase letter';
    }
    if (!/[0-9]/.test(password)) {
      return 'Password must contain at least one number';
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
      return 'Password must contain at least one special character';
    }
    return undefined;
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    const passwordError = validatePassword(formData.newPassword);
    if (passwordError) {
      errors.newPassword = passwordError;
    }
    
    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (formData.newPassword !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear field error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: undefined
      }));
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      setIsSubmitting(true);
      await onCompleteNewPassword(formData.newPassword);
    } catch (error) {
      // Error is handled by parent component
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormDisabled = isLoading || isSubmitting;

  return (
    <Box margin="xxl">
      <Container
        header={
          <Header variant="h1">
            Set New Password
          </Header>
        }
      >
        <form onSubmit={handleSubmit}>
          <Form
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <Button
                  variant="primary"
                  formAction="submit"
                  loading={isFormDisabled}
                  disabled={isFormDisabled}
                >
                  Set Password
                </Button>
              </SpaceBetween>
            }
          >
            <SpaceBetween direction="vertical" size="l">
              <Alert
                statusIconAriaLabel="Info"
                type="info"
                header="Password Change Required"
              >
                You must change your temporary password before continuing.
              </Alert>

              {error && (
                <Alert
                  statusIconAriaLabel="Error"
                  type="error"
                  header="Error"
                >
                  {error.message}
                </Alert>
              )}
              
              <FormField
                label="New Password"
                errorText={formErrors.newPassword}
                description="Password must be at least 8 characters and contain uppercase, lowercase, number, and special character"
              >
                <Input
                  value={formData.newPassword}
                  onChange={({ detail }) => handleInputChange('newPassword', detail.value)}
                  placeholder="Enter new password"
                  type="password"
                  disabled={isFormDisabled}
                  invalid={!!formErrors.newPassword}
                  autoComplete="new-password"
                />
              </FormField>
              
              <FormField
                label="Confirm Password"
                errorText={formErrors.confirmPassword}
                description="Re-enter your new password"
              >
                <Input
                  value={formData.confirmPassword}
                  onChange={({ detail }) => handleInputChange('confirmPassword', detail.value)}
                  placeholder="Confirm new password"
                  type="password"
                  disabled={isFormDisabled}
                  invalid={!!formErrors.confirmPassword}
                  autoComplete="new-password"
                />
              </FormField>
            </SpaceBetween>
          </Form>
        </form>
      </Container>
    </Box>
  );
};

export default NewPasswordForm;
