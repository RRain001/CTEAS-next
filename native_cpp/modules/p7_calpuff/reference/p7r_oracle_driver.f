c-----------------------------------------------------------------------
      program p7r_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7R FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7r_source_anchor.py: CTADJ2 and WALLTRAP.
c
c --- The driver supplies the terrain lookups as deterministic stubs and
c     fills the /GRID/ and /METHD/ state from the case line; the C++ test
c     mirrors the same stubs and state exactly.
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase r zpold xold yold xnew ynew szold bvf ws dgrid
c             relc1..relc5 reln1..reln5 elc eln
c             -> icase strain zpnew fracz lup
c     mode 2: icase syb sye z xb yb xe ye bvf ws dzval xgridm
c             iw11 iw21 iw31 iw12 iw22 iw32 el1 el2 rel5c rel5n
c             (ivalw(level,cell) for levels 1-3 and cells 1-2)
c             -> icase sye itrap
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'grid.puf'
      include 'methd.puf'
c
      integer mode,ios,icase,lup_i
      real r_i,zpold_i,xold_i,yold_i,xnew_i,ynew_i,szold_i,bvf_i,ws_i
      real dgrid_i,relc(5),reln(5),elc_i,eln_i
      real strain_o,zpnew_o,fracz_o
      real syb_i,sye_i,z_i,xb_i,yb_i,xe_i,ye_i,dzval_i,xgridm_i
      integer iw11,iw21,iw31,iw12,iw22,iw32,itrap_o
      real el1_i,el2_i,rel5c_i,rel5n_i
      logical lup_o
      integer kk
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7R oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,r_i,zpold_i,xold_i,yold_i,xnew_i,
     &                      ynew_i,szold_i,bvf_i,ws_i,dgrid_i,
     &                      relc(1),relc(2),relc(3),relc(4),relc(5),
     &                      reln(1),reln(2),reln(3),reln(4),reln(5),
     &                      elc_i,eln_i
         if(ios.ne.0) goto 999
         dgrid=dgrid_i
         do kk=1,5
            relief(kk,1,1,1)=relc(kk)
            relief(kk,2,1,1)=reln(kk)
         enddo
         elev(1,1,1)=elc_i
         elev(2,1,1)=eln_i
         call ctadj2(r_i,zpold_i,xold_i,yold_i,xnew_i,ynew_i,szold_i,
     &               bvf_i,ws_i,.FALSE.,strain_o,zpnew_o,fracz_o,
     &               lup_o)
         write(*,'(i8,3(1x,es20.12),1x,i4)') icase,strain_o,zpnew_o,
     &      fracz_o,INT(MERGE(1.0,0.0,lup_o))
         goto 10
      endif
c
 20   continue
      read(*,*,iostat=ios) icase,syb_i,sye_i,z_i,xb_i,yb_i,xe_i,ye_i,
     &                     bvf_i,ws_i,dzval_i,xgridm_i,iw11,iw21,iw31,
     &                     iw12,iw22,iw32,el1_i,el2_i,rel5c_i,rel5n_i
      if(ios.ne.0) goto 999
      dzval=dzval_i
      xgridm(1)=xgridm_i
      ivalw(1,1,1,1)=iw11
      ivalw(2,1,1,1)=iw21
      ivalw(3,1,1,1)=iw31
      ivalw(1,2,1,1)=iw12
      ivalw(2,2,1,1)=iw22
      ivalw(3,2,1,1)=iw32
      relief(5,1,1,1)=rel5c_i
      relief(5,2,1,1)=rel5n_i
      elev(1,1,1)=el1_i
      elev(2,1,1)=el2_i
      call walltrap(.FALSE.,syb_i,sye_i,z_i,xb_i,yb_i,xe_i,ye_i,bvf_i,
     &              ws_i,itrap_o)
      write(*,'(i8,1x,es20.12,1x,i4)') icase,sye_i,itrap_o
      goto 20
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine getcell(acall,axy,idom,x,y,dx,dy,icell,jcell,kdom)
c-----------------------------------------------------------------------
c --- Deterministic GETELEV/GETCELL stubs for the oracle: the first met cell
c     holds x < 0.5 and the second holds x >= 0.5. The C++ test injects the
c     identical mapping.
      character*12 acall,axy
      integer idom,icell,jcell,kdom
      real x,y,dx,dy
      if(x.LT.0.5) then
         icell=1
      else
         icell=2
      endif
      jcell=1
      kdom=1
      return
      end
c-----------------------------------------------------------------------
      subroutine getelev(x,y,z)
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'methd.puf'
      real x,y,z
      if(x.LT.0.5) then
         z=elev(1,1,1)
      else
         z=elev(2,1,1)
      endif
      return
      end
