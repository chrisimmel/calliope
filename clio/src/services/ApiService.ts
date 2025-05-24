import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { isPlatform } from '../utils/platform';
import { getSelectedServerConfig, ServerConfig } from '../utils/serverConfig';

/**
 * Service to handle API interactions with the Calliope backend
 */
class ApiService {
  private apiClient: AxiosInstance;
  private static instance: ApiService;
  private currentServerConfig: ServerConfig;

  private constructor() {
    // Get the server configuration based on environment and user selection
    this.currentServerConfig = getSelectedServerConfig();
    const baseURL = this.getBaseUrl();
    
    this.apiClient = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
        'X-Api-Key': 'xyzzy'
      }
    });
    
    // Log the base URL on initialization
    console.log(`ApiService initialized with baseURL: ${baseURL}`);
    
    // Add request interceptor for logging in development
    this.apiClient.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`, {
          headers: config.headers,
          params: config.params,
          data: config.data
        });
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Add response interceptor for logging and auto-retry with different host
    this.apiClient.interceptors.response.use(
      (response) => {
        console.log(`API Response (${response.status}): ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          data: response.data
        });
        return response;
      },
      (error) => {
        const isNetworkError = !error.response && error.message === 'Network Error';
        
        console.error('API Response Error:', error.message, {
          status: error.response?.status,
          data: error.response?.data,
          config: error.config?.url,
          isNetworkError
        });
        
        // More detailed network error information
        if (isNetworkError) {
          console.error('Network Error Details:', {
            baseURL: this.apiClient.defaults.baseURL,
            serverConfig: this.currentServerConfig,
            url: error.config?.url,
            platform: isPlatform.capacitor() ? (isPlatform.ios() ? 'iOS' : 'Android') : 'Web',
            userAgent: window.navigator.userAgent
          });
          
          // Log detailed error information
          this.logConnectionError(error);
        }
        
        return Promise.reject(error);
      }
    );
  }

  /**
   * Known iOS simulator - host connectivity options
   * These are different ways to connect from iOS simulator to the host machine
   * We'll try each of these in sequence
   */
  private readonly iosHostOptions = [
    // Special case for iOS simulator (most reliable method)
    'http://0.0.0.0:8008',
    'http://localhost:8008', 
    'http://127.0.0.1:8008',
    'http://host.docker.internal:8008',
    // Add your Mac's actual local network IP below (find with 'ifconfig en0')
    // 'http://192.168.1.X:8008'
  ];
  
  /**
   * Current iOS host option index
   */
  private iosHostOptionIndex = 0;
  
  /**
   * Updates the API client to use a new server configuration
   * This should be called when the user changes the server selection
   */
  public updateServerConfig(serverConfig: ServerConfig): void {
    // Store the new server configuration
    this.currentServerConfig = serverConfig;
    
    // Update the API client's base URL
    this.apiClient.defaults.baseURL = this.getBaseUrl();
    
    console.log(`ApiService updated to use server: ${serverConfig.name} (${this.apiClient.defaults.baseURL})`);
  }
  
  /**
   * Get the appropriate base URL depending on the environment
   */
  private getBaseUrl(): string {
    // If running in Capacitor (mobile app), use the full URL from the server config
    if (isPlatform.capacitor()) {
      return this.currentServerConfig.url;
    } else {
      // Web - use relative URLs since we're serving from the same origin
      return '';
    }
  }
  
  /**
   * Log connection error details
   */
  private logConnectionError(error: any): void {
    console.error('Connection error details:', {
      baseURL: this.apiClient.defaults.baseURL,
      serverConfig: this.currentServerConfig,
      message: error.message,
      code: error.code,
      isIOS: isPlatform.ios(),
      isAndroid: isPlatform.android(),
      isWeb: isPlatform.web(),
      userAgent: window.navigator.userAgent
    });
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  /**
   * Get the current server configuration
   */
  public getCurrentServerConfig(): ServerConfig {
    return this.currentServerConfig;
  }

  /**
   * GET request
   */
  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.apiClient.get<T>(url, config);
    return response.data;
  }

  /**
   * POST request
   */
  public async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.apiClient.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT request
   */
  public async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.apiClient.put<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE request
   */
  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.apiClient.delete<T>(url, config);
    return response.data;
  }

  /**
   * Get the Axios instance for advanced use cases
   */
  public getAxiosInstance(): AxiosInstance {
    return this.apiClient;
  }
}

export default ApiService.getInstance();