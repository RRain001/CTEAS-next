c-----------------------------------------------------------------------
      program p7w_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7W FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor unit RISEWIND with
c     deterministic GRISE and ADVECT stubs so that the comparison
c     isolates RISEWIND's own iteration.
c
c --- Case line (list directed):
c     icase xbeg xfinal zfinal dzb dt ufnl vfnl ncount
c           h0 hr lr a0 a1 a2 b0 b1 b2
c     GRISE(x)      = h0 + hr*(1-exp(-x/lr))
c     ADVECT(zb,zt) = (a0 + a1*zb + a2*zt, b0 + b1*zb + b2*zt)
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'puff.puf'
      include 'slug.puf'
c
      integer icase,ios,ncount_i,ii
      real xbeg_i,xfinal_i,zfinal_i,dzb_i,dt_i,ufnl_i,vfnl_i
      real h0_i,hr_i,lr_i,a0_i,a1_i,a2_i,b0_i,b1_i,b2_i
      real u_o,v_o,ws_o
      logical ldbhr
c
      common /p7wstub/ sh0,shr,slr,sa0,sa1,sa2,sb0,sb1,sb2
c
 10   read(*,*,iostat=ios) icase,xbeg_i,xfinal_i,zfinal_i,dzb_i,dt_i,
     &                     ufnl_i,vfnl_i,ncount_i,h0_i,hr_i,lr_i,
     &                     a0_i,a1_i,a2_i,b0_i,b1_i,b2_i
      if(ios.ne.0) goto 999
      ii=1
      xtotb(ii)=xbeg_i
      xtote(ii)=xbeg_i
      xfinal(ii)=xfinal_i
      zfinal(ii)=zfinal_i
      ht0(ii)=h0_i
      sh0=h0_i
      shr=hr_i
      slr=lr_i
      sa0=a0_i
      sa1=a1_i
      sa2=a2_i
      sb0=b0_i
      sb1=b1_i
      sb2=b2_i
      ldbhr=.FALSE.
      u_o=ufnl_i
      v_o=vfnl_i
      ws_o=SQRT(ufnl_i**2+vfnl_i**2)
      call risewind(ldbhr,.TRUE.,ncount_i,dzb_i,ii,1,1,1,0.25,-49.5,
     &              231.0,4,dt_i,u_o,v_o,ws_o)
      write(*,'(i8,3(1x,es20.12))') icase,u_o,v_o,ws_o
      goto 10
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine grise(x,htgrise,risefac)
c-----------------------------------------------------------------------
      real x,htgrise,risefac
      common /p7wstub/ sh0,shr,slr,sa0,sa1,sa2,sb0,sb1,sb2
      htgrise=sh0+shr*(1.0-EXP(-x/slr))
      risefac=1.0
      return
      end
c-----------------------------------------------------------------------
      subroutine advect(ldbg,ix,iy,mdom,z0m,el,dpbl,istab,ht,zbot,
     &                  ztop,uadv,vadv)
c-----------------------------------------------------------------------
      logical ldbg
      integer ix,iy,mdom,istab
      real z0m,el,dpbl,ht,zbot,ztop,uadv,vadv
      common /p7wstub/ sh0,shr,slr,sa0,sa1,sa2,sb0,sb1,sb2
      uadv=sa0+sa1*zbot+sa2*ztop
      vadv=sb0+sb1*zbot+sb2*ztop
      return
      end
