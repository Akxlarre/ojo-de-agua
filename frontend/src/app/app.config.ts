import { ApplicationConfig, importProvidersFrom } from "@angular/core";
import {
  provideRouter,
  withComponentInputBinding,
  withViewTransitions,
} from "@angular/router";
import { provideAnimationsAsync } from "@angular/platform-browser/animations/async";
import { providePrimeNG } from "primeng/config";
import Aura from "@primeng/themes/aura";
import { MessageService, ConfirmationService } from "primeng/api";
import {
  LucideAngularModule,
  // ── Boilerplate (dashboard, kpi-card, sidebar, alert-card) ──
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BarChart2,
  CheckCircle,
  ChevronRight,
  Download,
  LayoutDashboard,
  Plus,
  Settings,
  TrendingDown,
  TrendingUp,
  User,
  Users,
  // ── Shell support (topbar, login, mobile drawer) ──
  Bell,
  LogOut,
  Menu,
  Search,
  X,
  // ── Acciones comunes ──
  Check,
  Edit,
  Info,
  Trash2,
  // ── Navegación & GIS ──
  ArrowLeft,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  CloudSnow,
  GitBranch,
  Home,
  Layers,
  Map,
  Sliders,
  // ── Contenido & Auditoría ──
  Archive,
  Award,
  Banknote,
  BookOpen,
  Brain,
  Briefcase,
  Calculator,
  Calendar,
  ClipboardCheck,
  ClipboardList,
  Clock,
  CreditCard,
  DollarSign,
  FilePlus,
  FileSpreadsheet,
  FileText,
  Flag,
  FolderOpen,
  Image,
  Monitor,
  Receipt,
  Truck,
  Upload,
  Wallet,
  Wrench,
  // ── Acciones extendidas ──
  Copy,
  Eye,
  EyeOff,
  Filter,
  MoreHorizontal,
  MoreVertical,
  RefreshCw,
  Save,
  Share2,
  // ── Comunicación ──
  BellOff,
  Mail,
  MessageCircle,
  Send,
  // ── Estado & Legal ──
  Ban,
  Circle,
  CircleAlert,
  CircleCheck,
  HelpCircle,
  Loader,
  Shield,
  ShieldCheck,
  Star,
  Tag,
  UserCheck,
  UserMinus,
  XCircle,
  // ── Tema ──
  Moon,
  Sun,
} from "lucide-angular";

import { routes } from "./app.routes";
import { provideCoreAuth } from "@core/auth/provide-core-auth";

/**
 * Configuración principal de la aplicación.
 *
 * provideCoreAuth() ya incluye provideHttpClient(withInterceptors([authInterceptor])).
 * NO añadas provideHttpClient() por separado o se duplicará.
 */
export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding(), withViewTransitions()),
    provideAnimationsAsync(),
    providePrimeNG({
      theme: {
        preset: Aura,
        options: {
          darkModeSelector: ".fake-dark-mode",
          cssLayer: {
            name: "primeng",
            order: "tailwind-base, primeng, tailwind-utilities",
          },
        },
      },
    }),
    provideCoreAuth(),
    MessageService,
    ConfirmationService,
    /**
     * Lucide Icons — Set curado SaaS (~48 íconos).
     *
     * Incluye los íconos del boilerplate + un set genérico para features SaaS.
     * Para añadir más: importar de 'lucide-angular' y agregar al objeto.
     * Referencia: https://lucide.dev/icons
     * Guía de iconos del DS: skills/design-system/SKILL.md
     */
    importProvidersFrom(
      LucideAngularModule.pick({
        // Boilerplate (dashboard, kpi-card, sidebar, alert-card)
        Activity,
        AlertCircle,
        AlertTriangle,
        ArrowRight,
        BarChart2,
        CheckCircle,
        ChevronRight,
        Download,
        LayoutDashboard,
        Plus,
        Settings,
        TrendingDown,
        TrendingUp,
        User,
        Users,
        // Shell support
        Bell,
        LogOut,
        Menu,
        Search,
        X,
        // Acciones comunes
        Check,
        Edit,
        Info,
        Trash2,
        // Navegación & GIS
        ArrowLeft,
        ChevronDown,
        ChevronLeft,
        ChevronUp,
        CloudSnow,
        GitBranch,
        Home,
        Layers,
        Map,
        Sliders,
        // Contenido & Auditoría
        Archive,
        Award,
        Banknote,
        BookOpen,
        Brain,
        Briefcase,
        Calculator,
        Calendar,
        ClipboardCheck,
        ClipboardList,
        Clock,
        CreditCard,
        DollarSign,
        FilePlus,
        FileSpreadsheet,
        FileText,
        Flag,
        FolderOpen,
        Image,
        Monitor,
        Receipt,
        Truck,
        Upload,
        Wallet,
        Wrench,
        // Acciones extendidas
        Copy,
        Eye,
        EyeOff,
        Filter,
        MoreHorizontal,
        MoreVertical,
        RefreshCw,
        Save,
        Share2,
        // Comunicación
        BellOff,
        Mail,
        MessageCircle,
        Send,
        // Estado & Legal
        Ban,
        Circle,
        CircleAlert,
        CircleCheck,
        HelpCircle,
        Loader,
        Shield,
        ShieldCheck,
        Star,
        Tag,
        UserCheck,
        UserMinus,
        XCircle,
        // Tema
        Moon,
        Sun,
      }),
    ),
  ],
};
