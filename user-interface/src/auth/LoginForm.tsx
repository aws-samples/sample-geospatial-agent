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

interface LoginFormProps {
  onSignIn: (username: string, password: string) => Promise<void>;
  isLoading: boolean;
  error?: AuthError | null;
}

interface FormData {
  username: string;
  password: string;
}

interface FormErrors {
  username?: string;
  password?: string;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSignIn, isLoading, error }) => {
  const [formData, setFormData] = useState<FormData>({
    username: '',
    password: ''
  });
  
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateForm = (): boolean => {
    const errors: FormErrors = {};
    
    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    }
    
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters long';
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
      await onSignIn(formData.username.trim(), formData.password);
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
            Geospatial Agent
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
                  Sign In
                </Button>
              </SpaceBetween>
            }
            errorText={error?.message}
            errorIconAriaLabel="Error"
          >
            <SpaceBetween direction="vertical" size="l">
              {error && (
                <Alert
                  statusIconAriaLabel="Error"
                  type="error"
                  header="Authentication Error"
                >
                  {error.message}
                </Alert>
              )}
              
              <FormField
                label="Username"
                errorText={formErrors.username}
                description="Enter your username or email address"
              >
                <Input
                  value={formData.username}
                  onChange={({ detail }) => handleInputChange('username', detail.value)}
                  placeholder="Enter username"
                  disabled={isFormDisabled}
                  invalid={!!formErrors.username}
                  autoComplete="username"
                />
              </FormField>
              
              <FormField
                label="Password"
                errorText={formErrors.password}
                description="Enter your password"
              >
                <Input
                  value={formData.password}
                  onChange={({ detail }) => handleInputChange('password', detail.value)}
                  placeholder="Enter password"
                  type="password"
                  disabled={isFormDisabled}
                  invalid={!!formErrors.password}
                  autoComplete="current-password"
                />
              </FormField>
            </SpaceBetween>
          </Form>
        </form>
      </Container>
    </Box>
  );
};

export default LoginForm;